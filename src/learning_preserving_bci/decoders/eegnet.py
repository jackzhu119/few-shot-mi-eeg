"""Small CPU training wrapper around Braindecode's official EEGNet."""

from __future__ import annotations

import inspect

import numpy as np
import torch
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_is_fitted
from torch.utils.data import DataLoader, TensorDataset

from ..utils.reproducibility import seed_everything


class EEGNetClassifier(ClassifierMixin, BaseEstimator):
    """A minimal reproducible EEGNet baseline, not a validated candidate method.

    Channel centering and scaling are learned from training data only. The
    default deliberately uses CPU, with a seeded minibatch generator. Runtime
    compatibility is checked against the installed Braindecode constructor;
    no substitute architecture is silently selected.
    """

    def __init__(
        self,
        n_channels: int,
        n_classes: int,
        n_times: int,
        sfreq: float,
        epochs: int = 10,
        batch_size: int = 32,
        learning_rate: float = 1e-3,
        seed: int = 42,
        device: str = "cpu",
    ):
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.n_times = n_times
        self.sfreq = sfreq
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.seed = seed
        self.device = device

    def _array(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float32)
        if X.ndim != 3 or X.shape[1:] != (self.n_channels, self.n_times):
            raise ValueError("X must have shape (trials, n_channels, n_times)")
        if not len(X) or not np.isfinite(X).all():
            raise ValueError("X must be nonempty and finite")
        return X

    def _build_model(self):
        import braindecode.models as models

        model_class = getattr(models, "EEGNet", None)
        if model_class is None:
            model_class = getattr(models, "EEGNetv4", None)
        if model_class is None:
            raise RuntimeError("Installed Braindecode exposes neither EEGNet nor EEGNetv4")
        signature = inspect.signature(model_class).parameters
        modern = {
            "n_chans": self.n_channels,
            "n_outputs": self.n_classes,
            "n_times": self.n_times,
            "sfreq": self.sfreq,
            "final_conv_length": "auto",
        }
        legacy = {
            "in_chans": self.n_channels,
            "n_classes": self.n_classes,
            "input_window_samples": self.n_times,
            "final_conv_length": "auto",
        }
        kwargs = modern if "n_chans" in signature else legacy
        kwargs = {key: value for key, value in kwargs.items() if key in signature}
        self.architecture_ = f"braindecode.models.{model_class.__name__}"
        return model_class(**kwargs).to(self.device)

    @staticmethod
    def _logits(model, batch):
        logits = model(batch)
        # Older Braindecode releases return singleton spatial/time dimensions.
        while logits.ndim > 2 and logits.shape[-1] == 1:
            logits = logits.squeeze(-1)
        if logits.ndim != 2:
            raise RuntimeError("EEGNet must return one class vector per trial")
        return logits

    def fit(self, X: np.ndarray, y: np.ndarray):
        if self.device != "cpu":
            raise ValueError("This reproducible baseline currently supports device='cpu' only")
        if self.epochs < 1 or self.batch_size < 1 or self.learning_rate <= 0:
            raise ValueError("epochs, batch_size, and learning_rate must be positive")
        seed_everything(self.seed)
        X = self._array(X)
        y = np.asarray(y)
        if y.ndim != 1 or len(y) != len(X):
            raise ValueError("y must contain one class label per trial")
        self.classes_, encoded = np.unique(y, return_inverse=True)
        if len(self.classes_) != self.n_classes:
            raise ValueError("Training data must contain exactly n_classes distinct labels")
        self.channel_mean_ = X.mean(axis=(0, 2), keepdims=True)
        self.channel_scale_ = X.std(axis=(0, 2), keepdims=True).clip(min=1e-6)
        self.model_ = self._build_model()
        features = torch.from_numpy((X - self.channel_mean_) / self.channel_scale_)
        labels = torch.as_tensor(encoded, dtype=torch.long)
        generator = torch.Generator().manual_seed(self.seed)
        loader = DataLoader(
            TensorDataset(features, labels),
            batch_size=self.batch_size,
            shuffle=True,
            generator=generator,
            num_workers=0,
        )
        optimizer = torch.optim.Adam(self.model_.parameters(), lr=self.learning_rate)
        loss_function = torch.nn.CrossEntropyLoss()
        self.loss_history_ = []
        self.model_.train()
        for _ in range(self.epochs):
            total_loss = 0.0
            for batch, target in loader:
                optimizer.zero_grad(set_to_none=True)
                loss = loss_function(self._logits(self.model_, batch), target)
                if not torch.isfinite(loss):
                    raise RuntimeError("EEGNet training produced a nonfinite loss")
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * len(batch)
            self.loss_history_.append(total_loss / len(X))
        self.model_.eval()
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        check_is_fitted(self, ["model_", "classes_", "channel_mean_", "channel_scale_"])
        X = self._array(X)
        normalized = (X - self.channel_mean_) / self.channel_scale_
        probabilities = []
        self.model_.eval()
        with torch.no_grad():
            for start in range(0, len(X), self.batch_size):
                batch = torch.from_numpy(normalized[start : start + self.batch_size])
                logits = self._logits(self.model_, batch)
                probabilities.append(torch.softmax(logits, dim=1).cpu().numpy())
        return np.concatenate(probabilities)

    def predict(self, X: np.ndarray) -> np.ndarray:
        probabilities = self.predict_proba(X)
        return self.classes_[probabilities.argmax(axis=1)]
