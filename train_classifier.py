"""
train_classifier.py

Training script matching Section 3.3 ("Diagram Classification Model") of
the paper exactly:
  - Transfer learning on MobileNetV2 (Sandler et al., 2018)
  - Feature extractor frozen, single FC linear layer head for 7 classes
  - 30 epochs, Adam optimizer (lr=0.001), cross-entropy loss
  - Reports validation accuracy + per-class precision/recall/F1 (Table VI)
  - Also supports the weighted cross-entropy experiment described in the
    paper (which the paper found did NOT help: 83.7% vs 84.3% unweighted)

Usage (explicit train/val split, e.g. your diagram_dataset/train +
diagram_dataset/val layout):

    python train_classifier.py \
        --train-dir app/diagram_dataset/train \
        --val-dir app/diagram_dataset/val \
        --epochs 30

Both directories must contain the same 7 class subfolders:
    anatomical/  bar_chart/  circuit/  flowchart/  geometric/
    line_chart/  pie_chart/

Trained weights are saved to app/models/diagram_classifier.pt, which
diagram_classifier.py picks up automatically at inference time.
"""
import argparse
import os

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

from app.diagram_classifier import CLASSES, _build_model, WEIGHTS_PATH

TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

EVAL_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def compute_class_weights(dataset, num_classes):
    """weight = total_samples / (num_classes * class_count) — as in paper."""
    counts = [0] * num_classes
    for _, label in dataset.samples:
        counts[label] += 1
    total = sum(counts)
    weights = [total / (num_classes * c) if c > 0 else 0.0 for c in counts]
    return torch.tensor(weights, dtype=torch.float32)


def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            outputs = model(images)
            preds = outputs.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())

    acc = accuracy_score(all_labels, all_preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, labels=list(range(len(CLASSES))), zero_division=0
    )
    return acc, precision, recall, f1


def _check_class_alignment(train_ds, val_ds):
    expected = set(CLASSES)
    train_found = set(train_ds.classes)
    val_found = set(val_ds.classes)

    if train_found != expected:
        print(f"WARNING: train classes {sorted(train_found)} don't match expected {sorted(expected)}")
    if val_found != expected:
        print(f"WARNING: val classes {sorted(val_found)} don't match expected {sorted(expected)}")
    if train_ds.class_to_idx != val_ds.class_to_idx:
        raise SystemExit(
            "train/val class-to-index mappings differ — this would silently "
            "corrupt training. Make sure both folders contain exactly the "
            "same 7 subfolder names."
        )


def train(train_dir, val_dir, epochs, use_weighted_loss, device):
    train_dataset = datasets.ImageFolder(train_dir, transform=TRAIN_TRANSFORM)
    val_dataset = datasets.ImageFolder(val_dir, transform=EVAL_TRANSFORM)
    _check_class_alignment(train_dataset, val_dataset)

    print(f"Train images: {len(train_dataset)} | Val images: {len(val_dataset)}")
    for cls, idx in train_dataset.class_to_idx.items():
        train_count = sum(1 for _, label in train_dataset.samples if label == idx)
        val_count = sum(1 for _, label in val_dataset.samples if label == idx)
        print(f"  {cls:12s} train={train_count:4d}  val={val_count:4d}")

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    model = _build_model().to(device)
    optimizer = torch.optim.Adam(model.classifier.parameters(), lr=0.001)

    if use_weighted_loss:
        weights = compute_class_weights(train_dataset, len(CLASSES)).to(device)
        criterion = nn.CrossEntropyLoss(weight=weights)
    else:
        criterion = nn.CrossEntropyLoss()

    best_acc = 0.0
    best_state = None
    best_epoch = 0

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)

        epoch_loss = running_loss / len(train_dataset)
        val_acc, precision, recall, f1 = evaluate(model, val_loader, device)
        print(f"Epoch {epoch:2d}/{epochs} | train_loss={epoch_loss:.4f} | val_acc={val_acc:.4f}")

        if val_acc > best_acc:
            best_acc = val_acc
            best_state = model.state_dict()
            best_epoch = epoch

    print(f"\nBest validation accuracy: {best_acc:.4f} (epoch {best_epoch})")
    print("\nPer-class results at best epoch:")
    model.load_state_dict(best_state)
    val_acc, precision, recall, f1 = evaluate(model, val_loader, device)
    for i, cls in enumerate(train_dataset.classes):
        print(f"  {cls:12s} precision={precision[i]:.3f} recall={recall[i]:.3f} f1={f1[i]:.3f}")

    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    torch.save(best_state, WEIGHTS_PATH)
    print(f"\nSaved best weights to {WEIGHTS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the diagram classifier (Section 3.3)")
    parser.add_argument("--train-dir", required=True, help="Path to ImageFolder-structured training set")
    parser.add_argument("--val-dir", required=True, help="Path to ImageFolder-structured validation set")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--weighted-loss", action="store_true",
                         help="Use weighted cross-entropy (paper found this did NOT help: 83.7%% vs 84.3%%)")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    train(args.train_dir, args.val_dir, args.epochs, args.weighted_loss, device)