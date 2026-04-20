import pandas as pd
import streamlit as st
import json
import os

ANNOTATIONS_PER_ROW = 3
ROWS_PER_ANNOTATOR = 10
STORE_FILE = 'annotations.json'

POLITICS_SUBCATEGORIES = [
    ('policy_discussion', 'Policy Discussion', 'Discussion of political issues without attacking opponents'),
    ('policy_criticism', 'Policy Criticism', 'Being critical of a policy or political position'),
    ('personal_attacks', 'Personal Attacks', 'Attacking or disrespecting a person or party'),
    ('accomplishments', 'Accomplishments', 'Taking credit for legislation, funding, or other accomplishments'),
    ('bipartisanship', 'Bipartisanship', 'Collaboration and finding common ground across party lines'),
]

FINANCE_SUBCATEGORIES = [
    ('financial_fraud', 'Financial Fraud and Scams', ''),
    ('trading_misinformation', 'Trading Platforms and Misinformation', ''),
    ('misleading_advertising', 'Misleading Financial Advertising', ''),
    ('insider_trading', 'Insider Trading and Market Manipulation', ''),
    ('deceptive_lending', 'Deceptive Practices in Credit and Lending', ''),
    ('identity_theft', 'Identity Theft and Financial Information Breaches', ''),
]


def get_prolific_id():
    params = st.query_params
    return params.get("PROLIFIC_PID") or params.get("prolific_pid")


@st.cache_data
def load_texts(csv_path):
    df = pd.read_csv(csv_path)
    text_col = next((c for c in ['text', 'note', 'message', 'content', 'post'] if c in df.columns), None)
    if text_col is None:
        return None, df.columns.tolist()
    return df[text_col].dropna().tolist(), None


def load_store():
    if os.path.exists(STORE_FILE):
        with open(STORE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data.setdefault('assignments', {})
        data.setdefault('annotations', {})
        return data
    return {'assignments': {}, 'annotations': {}}


def save_store(data):
    with open(STORE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def assign_rows(prolific_id, texts, store):
    """Assign up to ROWS_PER_ANNOTATOR eligible rows to a prolific_id and persist."""
    if prolific_id in store['assignments']:
        return store['assignments'][prolific_id]

    # Sort eligible rows: prefer those closest to ANNOTATIONS_PER_ROW (fill up rows first)
    eligible = []
    for i, _ in enumerate(texts):
        existing = store['annotations'].get(str(i), [])
        done_by = [a['prolific_id'] for a in existing]
        if prolific_id not in done_by and len(existing) < ANNOTATIONS_PER_ROW:
            eligible.append((i, len(existing)))

    eligible.sort(key=lambda x: -x[1])  # prioritise rows with most annotations
    assigned = [i for i, _ in eligible[:ROWS_PER_ANNOTATOR]]
    store['assignments'][prolific_id] = assigned
    save_store(store)
    return assigned


def get_pending(prolific_id, assigned, store):
    """Return assigned row indices not yet annotated by this prolific_id."""
    return [
        i for i in assigned
        if prolific_id not in [a['prolific_id'] for a in store['annotations'].get(str(i), [])]
    ]


def main():
    st.title("Misinformation Domain Annotation Tool")

    # --- Prolific ID from URL ---
    prolific_id = get_prolific_id()
    if not prolific_id:
        st.error("No Prolific ID found in URL. Please access this page via your Prolific study link.")
        st.caption("Expected URL format: `http://localhost:8501/?PROLIFIC_PID=abc123`")
        prolific_id = st.text_input("Or enter your Prolific ID manually for testing:")
        if not prolific_id:
            return

    st.sidebar.markdown(f"**Prolific ID:** `{prolific_id}`")

    # --- CSV path ---
    csv_path = st.sidebar.text_input("CSV file path", value="data.csv")
    if not os.path.exists(csv_path):
        st.warning(f"CSV not found at `{csv_path}`.")
        return

    texts, err_cols = load_texts(csv_path)
    if texts is None:
        st.error(f"No text column found. Expected one of: text, note, message, content, post")
        st.write("Available columns:", err_cols)
        return

    # --- Load store & assign rows ---
    store = load_store()
    assigned = assign_rows(prolific_id, texts, store)
    pending = get_pending(prolific_id, assigned, store)

    st.sidebar.markdown(f"**Assigned:** {len(assigned)} rows")
    st.sidebar.markdown(f"**Remaining:** {len(pending)} rows")

    if not pending:
        st.success("You have completed all your assigned items. Thank you!")
        st.balloons()
        return

    # --- Session state ---
    for key, default in [('local_idx', 0), ('domain', None), ('subcategory', None)]:
        if key not in st.session_state:
            st.session_state[key] = default

    # Clamp index
    if st.session_state.local_idx >= len(pending):
        st.session_state.local_idx = len(pending) - 1

    row_idx = pending[st.session_state.local_idx]
    current_text = texts[row_idx]

    # --- Progress ---
    done = len(assigned) - len(pending) + st.session_state.local_idx
    total = len(assigned)
    st.write(f"**Item {done + 1} of {total}**")
    st.progress((done + 1) / total)

    # --- Text display ---
    st.subheader("Text to annotate:")
    st.info(current_text)

    # --- Step 1: Domain ---
    st.subheader("Step 1 — Select Domain")
    col_pol, col_fin = st.columns(2)
    with col_pol:
        label = "✅ Politics" if st.session_state.domain == 'politics' else "Politics"
        if st.button(label, key="domain_politics", use_container_width=True):
            st.session_state.domain = None if st.session_state.domain == 'politics' else 'politics'
            st.session_state.subcategory = None
            st.rerun()
    with col_fin:
        label = "✅ Finance" if st.session_state.domain == 'finance' else "Finance"
        if st.button(label, key="domain_finance", use_container_width=True):
            st.session_state.domain = None if st.session_state.domain == 'finance' else 'finance'
            st.session_state.subcategory = None
            st.rerun()

    # --- Step 2: Subcategory ---
    if st.session_state.domain == 'politics':
        st.subheader("Step 2 — Politics Subcategory")
        for tag, label, description in POLITICS_SUBCATEGORIES:
            is_selected = st.session_state.subcategory == tag
            col1, col2 = st.columns([1, 3])
            with col1:
                btn_label = f"✅ {label}" if is_selected else label
                if st.button(btn_label, key=f"sub_{tag}", use_container_width=True):
                    st.session_state.subcategory = None if is_selected else tag
                    st.rerun()
            with col2:
                st.caption(description)

    elif st.session_state.domain == 'finance':
        st.subheader("Step 2 — Finance Subcategory")
        for tag, label, _ in FINANCE_SUBCATEGORIES:
            is_selected = st.session_state.subcategory == tag
            btn_label = f"✅ {label}" if is_selected else label
            if st.button(btn_label, key=f"sub_{tag}", use_container_width=True):
                st.session_state.subcategory = None if is_selected else tag
                st.rerun()

    # --- Current selection summary ---
    if st.session_state.domain:
        sub = st.session_state.subcategory or "—"
        st.success(f"Selected: **{st.session_state.domain.title()}** / **{sub}**")

    # --- Navigation ---
    st.divider()
    can_save = st.session_state.domain is not None and st.session_state.subcategory is not None
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.local_idx == 0):
            st.session_state.local_idx -= 1
            st.session_state.domain = None
            st.session_state.subcategory = None
            st.rerun()

    with col2:
        if st.button("💾 Save & Next", disabled=not can_save, type="primary"):
            row_key = str(row_idx)
            store['annotations'].setdefault(row_key, [])
            # Update if this annotator already has an entry (shouldn't happen, but safe)
            existing_entries = store['annotations'][row_key]
            existing_entries = [e for e in existing_entries if e['prolific_id'] != prolific_id]
            existing_entries.append({
                'prolific_id': prolific_id,
                'domain': st.session_state.domain,
                'subcategory': st.session_state.subcategory,
            })
            store['annotations'][row_key] = existing_entries
            save_store(store)
            st.session_state.local_idx += 1
            st.session_state.domain = None
            st.session_state.subcategory = None
            st.rerun()

    with col3:
        if st.button("Skip ➡️", disabled=st.session_state.local_idx >= len(pending) - 1):
            st.session_state.local_idx += 1
            st.session_state.domain = None
            st.session_state.subcategory = None
            st.rerun()

    if not can_save:
        st.caption("Select both a domain and subcategory to enable Save.")

    # --- Export (sidebar) ---
    st.sidebar.divider()
    st.sidebar.subheader("Export")
    total_annotated = sum(len(v) for v in store['annotations'].values())
    st.sidebar.write(f"{total_annotated} annotation(s) across {len(store['annotations'])} rows")
    if st.sidebar.button("📥 Export to CSV"):
        rows = []
        for row_key, entries in store['annotations'].items():
            text = texts[int(row_key)]
            for entry in entries:
                rows.append({'row_id': row_key, 'text': text, **entry})
        csv = pd.DataFrame(rows).to_csv(index=False)
        st.sidebar.download_button("Download CSV", data=csv,
                                   file_name="annotated_misinformation.csv", mime="text/csv")


if __name__ == "__main__":
    main()
