"""Vision transfer runtime — backends extract features, OEC trains the head.

Merit: torchvision ResNet / Transformers CLIP for the backbone; PyTorch MLP head.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import train_mlp
from oec.neural.contracts import (
    ActivationName,
    DatasetSpec,
    DeviceSpec,
    LossName,
    NeuralModelSpec,
    NeuralTask,
    OptimizerName,
    OptimizerSpec,
    TrainingSpec,
)
from oec.neural.vision import (
    VisionBackboneName,
    VisionBackboneWeights,
    VisionTransferMode,
    VisionTransferSpec,
)


def _require_torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise TorchNotAvailableError(
            "torch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch


def _require_torchvision() -> Any:
    try:
        import torchvision
    except ImportError as exc:
        raise TorchNotAvailableError(
            "torchvision is required for backbone=resnet18. "
            "Install explicitly: uv pip install torchvision"
        ) from exc
    return torchvision


def run_vision_transfer(spec: VisionTransferSpec) -> dict[str, Any]:
    """Run one transfer mode and return comparable metrics + a head checkpoint."""
    torch = _require_torch()
    if spec.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = spec.device
        if device == "cuda" and not torch.cuda.is_available():
            raise TorchNotAvailableError("device=cuda requested but CUDA is not available")

    if spec.mode is VisionTransferMode.FROZEN_FEATURES:
        payload = _frozen_features(spec, device=device)
    else:
        payload = _finetune_pixels(spec, device=device)
    payload["device"] = device
    payload["mode"] = spec.mode.value
    payload["backbone"] = spec.backbone.value
    payload["backbone_weights"] = spec.backbone_weights.value
    payload["n_examples"] = len(spec.examples)
    payload["n_classes"] = spec.n_classes
    payload["seed"] = spec.seed
    return payload


def _frozen_features(spec: VisionTransferSpec, *, device: str) -> dict[str, Any]:
    features, labels, feature_dim, backend = _extract_features(spec, device=device)
    n_classes = spec.n_classes
    task = (
        NeuralTask.BINARY_CLASSIFICATION if n_classes == 2 else NeuralTask.MULTICLASS_CLASSIFICATION
    )
    result = train_mlp(
        DatasetSpec(x=features, y=[float(v) for v in labels], val_fraction=spec.val_fraction),
        NeuralModelSpec(
            architecture="mlp",
            input_dim=feature_dim,
            output_dim=1 if n_classes == 2 else n_classes,
            hidden_dims=list(spec.hidden_dims),
            activation=ActivationName.RELU,
        ),
        TrainingSpec(
            task=task,
            epochs=spec.epochs,
            batch_size=spec.batch_size,
            loss=LossName.BCE if n_classes == 2 else LossName.CROSS_ENTROPY,
            optimizer=OptimizerSpec(name=OptimizerName.ADAMW, lr=spec.lr),
            seed=spec.seed,
            device=DeviceSpec(device=device if device in {"cpu", "cuda"} else "cpu"),
            normalize_x=True,
        ),
    )
    return {
        "backend": backend,
        "feature_dim": feature_dim,
        "train_metrics": result.train_metrics,
        "val_metrics": result.val_metrics,
        "n_params": result.n_params,
        "epochs_ran": result.epochs_ran,
        "checkpoint": result.checkpoint,
        "normalize": result.normalize,
        "dataset_fingerprint": result.dataset_fingerprint,
        "message": "MLP head trained on frozen backbone features",
    }


def _extract_features(
    spec: VisionTransferSpec, *, device: str
) -> tuple[list[list[float]], list[int], int, str]:
    if spec.backbone is VisionBackboneName.RESNET18:
        return _resnet18_features(spec, device=device)
    return _clip_features(spec)


def _resnet18_features(
    spec: VisionTransferSpec, *, device: str
) -> tuple[list[list[float]], list[int], int, str]:
    torch = _require_torch()
    torchvision = _require_torchvision()
    from torchvision.models import ResNet18_Weights, resnet18

    weights = (
        ResNet18_Weights.IMAGENET1K_V1
        if spec.backbone_weights is VisionBackboneWeights.IMAGENET
        else None
    )
    model = resnet18(weights=weights)
    feature_dim = int(model.fc.in_features)
    extractor = torch.nn.Sequential(*list(model.children())[:-1]).to(device)
    extractor.eval()
    transform = _imagenet_transform(torchvision)
    feats: list[list[float]] = []
    labels: list[int] = []
    with torch.no_grad():
        for example in spec.examples:
            tensor = transform(_load_rgb(example.path)).unsqueeze(0).to(device)
            vec = extractor(tensor).flatten(1).cpu().tolist()[0]
            feats.append([float(v) for v in vec])
            labels.append(int(example.label))
    return feats, labels, feature_dim, "torchvision.resnet18"


def _clip_features(spec: VisionTransferSpec) -> tuple[list[list[float]], list[int], int, str]:
    from oec.foundation.contracts import FoundationModelSpec, VisionEmbeddingSpec, VisionImageInput
    from oec.foundation.runtime import vision_embed

    images = tuple(VisionImageInput(image_path=ex.path) for ex in spec.examples)
    raw = vision_embed(
        VisionEmbeddingSpec(
            model=FoundationModelSpec(model_id=spec.clip_model_id, revision=spec.clip_revision),
            images=images,
        )
    )
    vectors = raw.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        raise TorchNotAvailableError("CLIP vision_embed returned no vectors")
    feats = [[float(v) for v in row] for row in vectors]
    labels = [int(ex.label) for ex in spec.examples]
    return feats, labels, len(feats[0]), "transformers.clip"


def _finetune_pixels(spec: VisionTransferSpec, *, device: str) -> dict[str, Any]:
    if spec.backbone is not VisionBackboneName.RESNET18:
        raise TorchNotAvailableError(
            "finetune_head / finetune_last currently support backbone=resnet18"
        )
    torch = _require_torch()
    torchvision = _require_torchvision()
    from torchvision.models import ResNet18_Weights, resnet18

    weights = (
        ResNet18_Weights.IMAGENET1K_V1
        if spec.backbone_weights is VisionBackboneWeights.IMAGENET
        else None
    )
    model = resnet18(weights=weights)
    feature_dim = int(model.fc.in_features)
    head = _mlp_head(torch, feature_dim, list(spec.hidden_dims), spec.n_classes)
    model.fc = head
    for name, param in model.named_parameters():
        if (
            name.startswith("fc.")
            or spec.mode is VisionTransferMode.FINETUNE_LAST
            and name.startswith("layer4.")
        ):
            param.requires_grad = True
        else:
            param.requires_grad = False
    model = model.to(device)
    transform = _imagenet_transform(torchvision)
    tensors = [transform(_load_rgb(ex.path)) for ex in spec.examples]
    labels = torch.tensor([ex.label for ex in spec.examples], dtype=torch.long)
    dataset = torch.utils.data.TensorDataset(torch.stack(tensors), labels)
    n_val = int(round(len(dataset) * spec.val_fraction)) if spec.val_fraction > 0 else 0
    if 0 < n_val < len(dataset):
        n_train = len(dataset) - n_val
        train_set, val_set = torch.utils.data.random_split(
            dataset, [n_train, n_val], generator=torch.Generator().manual_seed(spec.seed)
        )
    else:
        train_set, val_set = dataset, None
    loader = torch.utils.data.DataLoader(train_set, batch_size=spec.batch_size, shuffle=True)
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=spec.lr)
    loss_fn = torch.nn.CrossEntropyLoss()
    torch.manual_seed(spec.seed)
    model.train()
    last_loss = 0.0
    for _ in range(spec.epochs):
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            last_loss = float(loss.detach().item())
    train_metrics = _accuracy(model, train_set, device, torch)
    train_metrics["loss"] = last_loss
    val_metrics = _accuracy(model, val_set, device, torch) if val_set is not None else None
    n_trainable = sum(int(p.numel()) for p in model.parameters() if p.requires_grad)
    return {
        "backend": "torchvision.resnet18",
        "feature_dim": feature_dim,
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "n_params": n_trainable,
        "epochs_ran": spec.epochs,
        "checkpoint": None,
        "message": f"pixel {spec.mode.value} on resnet18",
    }


def _mlp_head(torch: Any, input_dim: int, hidden: list[int], n_classes: int) -> Any:
    layers: list[Any] = []
    prev = input_dim
    for width in hidden:
        layers.extend((torch.nn.Linear(prev, width), torch.nn.ReLU(), torch.nn.Dropout(0.2)))
        prev = width
    layers.append(torch.nn.Linear(prev, n_classes))
    return torch.nn.Sequential(*layers)


def _imagenet_transform(torchvision: Any) -> Any:
    return torchvision.transforms.Compose(
        [
            torchvision.transforms.Resize((224, 224)),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )


def _load_rgb(path: str) -> Any:
    from oec.foundation.contracts import VisionImageInput
    from oec.foundation.runtime import load_vision_image

    image = load_vision_image(VisionImageInput(image_path=path))
    return image.convert("RGB")


def _accuracy(model: Any, subset: Any, device: str, torch: Any) -> dict[str, float]:
    loader = torch.utils.data.DataLoader(subset, batch_size=16, shuffle=False)
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            pred = model(xb).argmax(dim=1)
            correct += int((pred == yb).sum().item())
            total += int(yb.numel())
    return {"accuracy": float(correct / total) if total else 0.0, "n": float(total)}
