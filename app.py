"""
Chimp ID Trainer — Streamlit app for zoo volunteers to learn and test
recognition of individual chimpanzees.

Expected folder structure:
    data_dir/
        ChimpName1/
            img1.jpg
            img2.jpg
            ...
        ChimpName2/
            ...

Usage:
    pip install streamlit pillow
    streamlit run app.py
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_dataset(data_dir: str) -> Dict[str, List[str]]:
    """Scan data_dir; each subfolder is one identity."""
    root = Path(data_dir).expanduser()
    if not root.is_dir():
        return {}
    dataset: Dict[str, List[str]] = {}
    for identity_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        images = sorted(
            str(p) for p in identity_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )
        if images:
            dataset[identity_dir.name] = images
    return dataset


def flat_image_list(dataset: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    """Return [(identity, image_path), ...] across the whole dataset."""
    return [(name, p) for name, paths in dataset.items() for p in paths]


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_state() -> None:
    defaults = {
        # Score
        "score_correct": 0,
        "score_total": 0,
        # Current test question
        "test_image": None,
        "test_answer": None,
        "test_options": [],
        "test_submitted": False,
        "test_selection": None,
        # Slideshow
        "slideshow_idx": 0,
        "slideshow_list": [],
        "slideshow_filter": "All",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def new_test_question(dataset: Dict[str, List[str]], n_options: int = 4) -> None:
    """Pick a random image and prepare its multiple-choice options."""
    identities = list(dataset.keys())
    if not identities:
        return

    answer = random.choice(identities)
    image_path = random.choice(dataset[answer])

    distractors = [i for i in identities if i != answer]
    random.shuffle(distractors)
    n_distract = min(n_options - 1, len(distractors))
    options = distractors[:n_distract] + [answer]
    random.shuffle(options)

    st.session_state.test_image = image_path
    st.session_state.test_answer = answer
    st.session_state.test_options = options
    st.session_state.test_submitted = False
    st.session_state.test_selection = None


# ---------------------------------------------------------------------------
# Learning mode
# ---------------------------------------------------------------------------

def learning_mode(dataset: Dict[str, List[str]]) -> None:
    st.header("Learning Mode")
    sub_mode = st.radio(
        "View", ["Slideshow", "Gallery"], horizontal=True, key="learning_sub_mode"
    )
    if sub_mode == "Slideshow":
        slideshow_view(dataset)
    else:
        gallery_view(dataset)


def slideshow_view(dataset: Dict[str, List[str]]) -> None:
    identities = ["All"] + list(dataset.keys())
    selected = st.selectbox("Filter by chimp", identities, key="slideshow_filter_select")

    # Rebuild list if the filter changed
    if selected != st.session_state.slideshow_filter or not st.session_state.slideshow_list:
        st.session_state.slideshow_filter = selected
        st.session_state.slideshow_idx = 0
        if selected == "All":
            st.session_state.slideshow_list = flat_image_list(dataset)
        else:
            st.session_state.slideshow_list = [(selected, p) for p in dataset[selected]]

    images = st.session_state.slideshow_list
    if not images:
        st.info("No images to show.")
        return

    idx = st.session_state.slideshow_idx % len(images)
    name, path = images[idx]
    st.image(path, caption=f"{name}   ({idx + 1} / {len(images)})", use_column_width=True)

    c_prev, c_shuf, c_next = st.columns(3)
    with c_prev:
        if st.button("◀ Previous", use_container_width=True):
            st.session_state.slideshow_idx = (idx - 1) % len(images)
            st.rerun()
    with c_shuf:
        if st.button("🔀 Shuffle", use_container_width=True):
            random.shuffle(st.session_state.slideshow_list)
            st.session_state.slideshow_idx = 0
            st.rerun()
    with c_next:
        if st.button("Next ▶", use_container_width=True):
            st.session_state.slideshow_idx = (idx + 1) % len(images)
            st.rerun()


def gallery_view(dataset: Dict[str, List[str]]) -> None:
    cols_per_row = st.slider("Images per row", 2, 6, 4)
    for name, paths in dataset.items():
        st.subheader(name)
        st.caption(f"{len(paths)} image{'s' if len(paths) != 1 else ''}")
        rows = [paths[i:i + cols_per_row] for i in range(0, len(paths), cols_per_row)]
        for row in rows:
            cols = st.columns(cols_per_row)
            for col, img_path in zip(cols, row):
                with col:
                    st.image(img_path, use_column_width=True)
        st.divider()


# ---------------------------------------------------------------------------
# Testing mode
# ---------------------------------------------------------------------------

def testing_mode(dataset: Dict[str, List[str]]) -> None:
    st.header("Testing Mode")

    n_options = st.sidebar.slider("Number of choices per question", 2, 8, 4)

    if st.session_state.test_image is None:
        new_test_question(dataset, n_options=n_options)

    # Center the image so it doesn't take up the full wide layout
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.image(st.session_state.test_image, caption="Who is this chimp?", use_column_width=True)

    if not st.session_state.test_submitted:
        choice = st.radio(
            "Your guess:",
            st.session_state.test_options,
            index=None,
            key=f"guess_{st.session_state.score_total}",
        )
        if st.button("Submit", type="primary", disabled=choice is None):
            st.session_state.test_selection = choice
            st.session_state.test_submitted = True
            st.session_state.score_total += 1
            if choice == st.session_state.test_answer:
                st.session_state.score_correct += 1
            st.rerun()
    else:
        if st.session_state.test_selection == st.session_state.test_answer:
            st.success(f"✅ Correct! That's **{st.session_state.test_answer}**.")
        else:
            st.error(
                f"❌ You guessed **{st.session_state.test_selection}**. "
                f"That was actually **{st.session_state.test_answer}**."
            )
        if st.button("Next question →", type="primary"):
            new_test_question(dataset, n_options=n_options)
            st.rerun()

    # Score footer
    st.divider()
    total = st.session_state.score_total
    correct = st.session_state.score_correct
    pct = (correct / total * 100) if total else 0.0
    st.metric(
        label="Score",
        value=f"{correct} / {total}",
        delta=f"{pct:.1f}%" if total else None,
    )

    if st.sidebar.button("Reset score"):
        st.session_state.score_correct = 0
        st.session_state.score_total = 0
        new_test_question(dataset, n_options=n_options)
        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Chimp ID Trainer", page_icon="🐵", layout="wide")
    init_state()

    st.title("🐵 Chimp ID Trainer")

    data_dir = st.sidebar.text_input(
        "Image folder",
        value="./chimp_images",
        help="A folder containing one subfolder per chimp.",
    )

    dataset = load_dataset(data_dir)

    if not dataset:
        st.warning(
            f"No images found in `{data_dir}`. "
            "Make sure the folder exists and contains subdirectories of images."
        )
        st.stop()

    n_ids = len(dataset)
    n_imgs = sum(len(v) for v in dataset.values())
    st.sidebar.caption(f"{n_ids} chimps · {n_imgs} images")

    mode = st.sidebar.radio("Mode", ["Learning", "Testing"], horizontal=True)
    if mode == "Learning":
        learning_mode(dataset)
    else:
        testing_mode(dataset)


if __name__ == "__main__":
    main()
