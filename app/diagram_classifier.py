"""
diagram_classifier.py

MobileNetV2-based diagram classification pipeline (Section 3.3).

Architecture: MobileNetV2 feature extractor (Sandler et al., 2018) frozen,
with a single fully-connected linear layer replacing the head for the
7-class output. Images are resized to 224x224 before inference, matching
training preprocessing.

Categories (paper, Section 3.2 / Table VI):
    bar_chart, line_chart, pie_chart, flowchart, anatomical, geometrical, circuit

Drop-in weights:
    Put your trained weights at app/models/diagram_classifier.pt and this
    module will load them automatically. Until then, the model runs with
    an ImageNet-pretrained MobileNetV2 backbone but a randomly-initialized
    classification head, purely so the rest of the app (routes,
    templates, description generation) is fully wired and testable — the
    predictions won't be meaningful until you swap in your real weights.

Template-driven descriptions: each class maps to a natural-language
template, filled in with generic phrasing per the "template driven
natural language descriptions" approach described in the paper (based on
Stangl, Kim and Yeh, 2020).
"""
import os
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

CLASSES = [
    "bar_chart",
    "line_chart",
    "pie_chart",
    "flowchart",
    "anatomical",
    "geometric",
    "circuit",
]

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "models", "diagram_classifier.pt")

IMAGE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

DESCRIPTION_TEMPLATES = {
    "bar_chart": (
        "This appears to be a bar chart. Bar charts compare values across "
        "different categories using rectangular bars, where the height or "
        "length of each bar represents its value."
    ),
    "line_chart": (
        "This appears to be a line chart. Line charts show how a value "
        "changes over a continuous range, usually time, by connecting data "
        "points with a line."
    ),
    "pie_chart": (
        "This appears to be a pie chart. Pie charts show how a whole is "
        "divided into parts, with each slice representing a category's "
        "share of the total."
    ),
    "flowchart": (
        "This appears to be a flowchart. Flowcharts represent a process or "
        "algorithm as a sequence of steps connected by arrows, often with "
        "decision points shown as diamonds."
    ),
    "anatomical": (
        "This appears to be an anatomical diagram. Anatomical diagrams "
        "label the parts of a biological structure, such as an organ or "
        "body system, usually with lines pointing to labelled regions."
    ),
    "geometric": (
        "This appears to be a geometric diagram. Geometric diagrams "
        "illustrate shapes, angles, or spatial relationships, often with "
        "labelled points, lines, or measurements."
    ),
    "circuit": (
        "This appears to be a circuit diagram. Circuit diagrams show how "
        "electronic components are connected using standardized symbols "
        "for elements such as resistors, batteries, and switches."
    ),
}

_model = None


def _build_model():
    # Standard transfer learning (Section 3.3): load ImageNet-pretrained
    # MobileNetV2, freeze the feature extractor, replace the head.
    # NOTE: this downloads the pretrained ImageNet weights (~14MB) the
    # first time it runs, so it needs internet access once; after that
    # torch caches them locally (~/.cache/torch/hub/checkpoints).
    try:
        weights = models.MobileNet_V2_Weights.IMAGENET1K_V1
        model = models.mobilenet_v2(weights=weights)
    except AttributeError:
        # Older torchvision versions use the pretrained=True argument instead.
        model = models.mobilenet_v2(pretrained=True)

    for param in model.features.parameters():
        param.requires_grad = False
    in_features = model.last_channel
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(in_features, len(CLASSES)),
    )
    return model


def load_model():
    global _model
    if _model is not None:
        return _model

    model = _build_model()
    if os.path.exists(WEIGHTS_PATH):
        state_dict = torch.load(WEIGHTS_PATH, map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()
    else:
        # No trained weights yet — model runs with random init so the
        # surrounding app is fully wired. Swap in real weights at
        # app/models/diagram_classifier.pt when ready.
        model.eval()
    _model = model
    return _model


def classify_image(image_path: str):
    """Returns (predicted_class, confidence, description)."""
    model = load_model()
    image = Image.open(image_path).convert("RGB")
    tensor = IMAGE_TRANSFORM(image).unsqueeze(0)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
        confidence, predicted_idx = torch.max(probs, dim=0)

    predicted_class = CLASSES[predicted_idx.item()]
    description = DESCRIPTION_TEMPLATES[predicted_class]
    return predicted_class, float(confidence.item()), description


def is_using_trained_weights() -> bool:
    return os.path.exists(WEIGHTS_PATH)