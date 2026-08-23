"""Closed neural architecture kinds (ADR 0047). Core-safe."""

from __future__ import annotations

from enum import StrEnum


class TensorKind(StrEnum):
    SCALAR = "scalar"
    VECTOR = "vector"
    SEQUENCE = "sequence"
    IMAGE_1D = "image_1d"
    IMAGE_2D = "image_2d"
    VOLUME_3D = "volume_3d"
    FEATURE_MAP_1D = "feature_map_1d"
    FEATURE_MAP_2D = "feature_map_2d"
    FEATURE_MAP_3D = "feature_map_3d"
    GRAPH = "graph"
    NODE_FEATURES = "node_features"
    GRAPH_EMBEDDING = "graph_embedding"
    LATENT = "latent"
    ANY = "any"


class NeuralFamily(StrEnum):
    FEEDFORWARD = "feedforward"
    CONVOLUTIONAL = "convolutional"
    RECURRENT = "recurrent"
    ATTENTION = "attention"
    TRANSFORMER = "transformer"
    GRAPH = "graph"
    AUTOENCODER = "autoencoder"
    KAN = "kan"
    SPIKING = "spiking"
    CONTINUOUS = "continuous"
    NEURAL_OPERATOR = "neural_operator"
    PHYSICS_INFORMED = "physics_informed"
    STRUCTURAL = "structural"


class BlockCategory(StrEnum):
    PRIMITIVE = "primitive"
    ACTIVATION = "activation"
    BLOCK = "block"
    MOTIF = "motif"
    ADAPTER = "adapter"
    MACRO = "macro"
