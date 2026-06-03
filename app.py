"""
ChimpLearn — Streamlit app for zoo volunteers to learn and test
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
    return [(name, p) for name, paths in dataset.items() for p in paths]


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_state() -> None:
    defaults = {
        "current_mode": None,       # None=splash, "browse", "learn", "test"
        # Browse
        "browse_selected_chimp": None,
        # Learn
        "learn_deck": [],
        "learn_image": None,
        "learn_answer": None,
        "learn_flipped": False,
        # Test
        "test_deck": [],
        "score_correct": 0,
        "score_total": 0,
        "test_image": None,
        "test_answer": None,
        "test_options": [],
        "test_submitted": False,
        "test_selection": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


# ---------------------------------------------------------------------------
# Splash screen
# ---------------------------------------------------------------------------

def splash_screen(dataset: Dict[str, List[str]]) -> None:
    n_ids = len(dataset)
    n_imgs = sum(len(v) for v in dataset.values())

    st.markdown(
        "<h1 style='text-align:center; padding-top:1em;'>🐵 ChimpLearn</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center; color:#888; font-size:1.1em;'>"
        f"{n_ids} chimpanzees · {n_imgs} photos</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("### 🖼️ Browse")
            st.markdown(
                "Explore a gallery of all chimpanzees, each shown with a representative "
                "photo. Click any chimp to browse their full photo collection."
            )
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Browse", use_container_width=True, type="primary", key="btn_browse"):
                st.session_state.current_mode = "browse"
                st.session_state.browse_selected_chimp = None
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("### 🃏 Learn")
            st.markdown(
                "Study with flashcards. You'll be shown a random chimpanzee photo — "
                "flip the card to reveal their name, then move on to the next."
            )
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Learn", use_container_width=True, type="primary", key="btn_learn"):
                st.session_state.current_mode = "learn"
                st.session_state.learn_image = None
                st.session_state.learn_flipped = False
                st.rerun()

    with col3:
        with st.container(border=True):
            st.markdown("### 🧪 Test")
            st.markdown(
                "Put your knowledge to the test! Identify each chimpanzee from "
                "multiple-choice options. Keep track of your score throughout the session!"
            )
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Test", use_container_width=True, type="primary", key="btn_test"):
                st.session_state.current_mode = "test"
                st.rerun()


# ---------------------------------------------------------------------------
# Browse mode
# ---------------------------------------------------------------------------

def browse_mode(dataset: Dict[str, List[str]]) -> None:
    if st.session_state.browse_selected_chimp is None:
        _browse_gallery(dataset)
    else:
        _browse_detail(dataset)


def _browse_gallery(dataset: Dict[str, List[str]]) -> None:
    col_back, col_head = st.columns([1, 6])
    with col_back:
        if st.button("← Home"):
            st.session_state.current_mode = None
            st.rerun()
    with col_head:
        st.header("Browse")

    st.caption(
        "Each chimpanzee is shown with one representative photo. "
        "Click **View photos →** to see their full collection as thumbnails."
    )
    st.divider()

    chimps = list(dataset.keys())
    cols_per_row = 3
    rows = [chimps[i:i + cols_per_row] for i in range(0, len(chimps), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for col, chimp in zip(cols, row):
            with col:
                rep_key = f"browse_rep_{chimp}"
                if rep_key not in st.session_state:
                    st.session_state[rep_key] = random.choice(dataset[chimp])
                st.image(st.session_state[rep_key], use_container_width=True)
                n = len(dataset[chimp])
                st.markdown(f"**{chimp}** · {n} photo{'s' if n != 1 else ''}")
                if st.button("View photos →", key=f"browse_btn_{chimp}", use_container_width=True):
                    st.session_state.browse_selected_chimp = chimp
                    st.rerun()
        st.write("")


def _browse_detail(dataset: Dict[str, List[str]]) -> None:
    chimp = st.session_state.browse_selected_chimp
    images = dataset[chimp]
    n = len(images)

    # Sticky name header — stays visible while scrolling through thumbnails
    st.markdown(
        f"""
        <style>
        .chimp-sticky-header {{
            position: sticky;
            top: 3.5rem;
            z-index: 100;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 0.5rem 0 0.4rem 0;
            border-bottom: 1px solid rgba(128,128,128,0.15);
        }}
        .chimp-sticky-header h2 {{ margin: 0; }}
        .chimp-sticky-header small {{ opacity: 0.55; }}
        </style>
        <div class="chimp-sticky-header">
            <h2>{chimp}</h2>
            <small>{n} photo{'s' if n != 1 else ''}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("← Gallery"):
        st.session_state.browse_selected_chimp = None
        st.rerun()

    st.divider()

    # Thumbnail grid — use browser pinch-to-zoom to enlarge
    cols_per_row = 4
    for row_start in range(0, n, cols_per_row):
        row = images[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, img_path in zip(cols, row):
            with col:
                st.image(img_path, use_container_width=True)


# ---------------------------------------------------------------------------
# Deck shuffle helper
# ---------------------------------------------------------------------------

def _deal(deck_key: str, dataset: Dict[str, List[str]]) -> Tuple[str, str]:
    """Return the next (identity, image_path) from a shuffled deck.
    Rebuilds and reshuffles automatically when the deck runs out."""
    if not st.session_state[deck_key]:
        deck = [(name, path) for name, paths in dataset.items() for path in paths]
        random.shuffle(deck)
        st.session_state[deck_key] = deck
    return st.session_state[deck_key].pop()


# ---------------------------------------------------------------------------
# Learn mode
# ---------------------------------------------------------------------------

def new_learn_card(dataset: Dict[str, List[str]]) -> None:
    answer, image_path = _deal("learn_deck", dataset)
    st.session_state.learn_image = image_path
    st.session_state.learn_answer = answer
    st.session_state.learn_flipped = False


def learn_mode(dataset: Dict[str, List[str]]) -> None:
    col_back, col_head = st.columns([1, 6])
    with col_back:
        if st.button("← Home"):
            st.session_state.current_mode = None
            st.rerun()
    with col_head:
        st.header("Learn — Flashcards")

    st.caption(
        "You'll see a random chimpanzee photo. "
        "Click **Reveal Name** to see who it is, then move to the next card."
    )
    st.divider()

    if st.session_state.learn_image is None:
        new_learn_card(dataset)

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.image(st.session_state.learn_image, use_container_width=True)

        if not st.session_state.learn_flipped:
            if st.button("🔍 Reveal Name", type="primary", use_container_width=True):
                st.session_state.learn_flipped = True
                st.rerun()
        else:
            st.markdown(
                f"<div style='text-align:center; font-size:1.8em; font-weight:bold;"
                f" padding:16px; border:3px solid #4caf50; border-radius:8px;"
                f" margin:8px 0; color:#4caf50;'>"
                f"{st.session_state.learn_answer}</div>",
                unsafe_allow_html=True,
            )
            st.write("")
            if st.button("Next Card →", type="primary", use_container_width=True):
                new_learn_card(dataset)
                st.rerun()


# ---------------------------------------------------------------------------
# Test mode
# ---------------------------------------------------------------------------

def new_test_question(dataset: Dict[str, List[str]], n_options: int = 4) -> None:
    identities = list(dataset.keys())
    if not identities:
        return
    answer, image_path = _deal("test_deck", dataset)
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


def testing_mode(dataset: Dict[str, List[str]]) -> None:
    n_options = 4

    col_back, col_head = st.columns([1, 6])
    with col_back:
        if st.button("← Home"):
            st.session_state.current_mode = None
            st.rerun()
    with col_head:
        st.header("Test")

    total = st.session_state.score_total
    correct = st.session_state.score_correct
    pct = (correct / total * 100) if total else 0.0
    score_str = f"**Score: {correct} / {total}** ({pct:.0f}%)" if total else "**Score: —**"
    col_score, col_reset = st.columns([5, 1])
    with col_score:
        st.markdown(score_str)
    with col_reset:
        if st.button("Reset", use_container_width=True):
            st.session_state.score_correct = 0
            st.session_state.score_total = 0
            st.session_state.test_image = None
            st.rerun()

    st.caption("Identify the chimpanzee from the choices below.")
    st.divider()

    if st.session_state.test_image is None:
        new_test_question(dataset, n_options=n_options)

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.image(st.session_state.test_image, caption="Who is this chimp?", use_container_width=True)

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="ChimpLearn", page_icon="🐵", layout="wide")
    init_state()

    dataset = load_dataset("./chimp_images")

    if not dataset:
        st.warning(
            f"No images found in `{data_dir}`. "
            "Make sure the folder exists and contains subdirectories of images."
        )
        st.stop()

    mode = st.session_state.current_mode

    if mode is None:
        splash_screen(dataset)
    elif mode == "browse":
        browse_mode(dataset)
    elif mode == "learn":
        learn_mode(dataset)
    elif mode == "test":
        testing_mode(dataset)


if __name__ == "__main__":
    main()
