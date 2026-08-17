---
id: neural.vision.transfer
version: 0.1.0
status: experimental
domain: neural
title: Vision transfer (pinned backbone + OEC head)
---

# Vision transfer

Requires `oec[neural]`. ResNet18 also needs **explicit** `torchvision`.
CLIP uses `oec[foundation]` and a 40-hex `clip_revision`.

The backbone is a backend (ImageNet ResNet or pinned CLIP). OEC trains the
head and can compare `frozen_features` (MLP on extracted vectors) with
`finetune_head` / `finetune_last`. Images are local paths only.
