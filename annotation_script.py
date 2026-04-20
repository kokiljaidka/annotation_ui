import pandas as pd
import streamlit as st
import json
import os

ANNOTATIONS_PER_ROW = 3
ROWS_PER_ANNOTATOR = 10
ASSIGNMENTS_FILE = 'assignments.json'

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
def load_df(csv_path):
    df = pd.read_csv(csv_path)
    text_col = next((c for c in ['text', 'note', 'message', 'content', 'post'] if c in df.columns), None)
    return df, text_col


def annotator_csv_path(prolific_id):
    return f'annotations_{prolific_id}.csv'


def load_annotator_df(prolific_id, orig_columns):
    path = annotator_csv_path(prolific_id)
    if os.path.exists(path):
        return pd.read_csv(path)
    cols = list(orig_columns) + ['row_id', 'prolific_id', 'domain', 'subcategory']
    return pd.DataFrame(columns=cols)


def get_annotated_row_ids(prolific_id, orig_columns):
    ann_df = load_annotator_df(prolific_id, orig_columns)
    if 'row_id' in ann_df.columns and len(ann_df):
        return set(ann_df['row_id'].astype(str).tolist())
    return set()


def save_annotation(prolific_id, row_id, orig_row, domain, subcategory):
    path = annotator_csv_path(prolific_id)
    new_row = {**orig_row, 'row_id': row_id, 'prolific_id': prolific_id,
               'domain': domain, 'subcategory': subcategory}
    if os.path.exists(path):
        existing = pd.read_csv(path)
        existing = existing[existing['row_id'].astype(str) != str(row_id)]
        updated = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    else:
        updated = pd.DataFrame([new_row])
    updated.to_csv(path, index=False)


def load_assignments():
    if os.path.exists(ASSIGNMENTS_FILE):
        with open(ASSIGNMENTS_FILE, 'r') as f:
            data = json.load(f)
        data.setdefault('assignments', {})
        data.setdefault('annotation_counts', {})
        return data
    return {'assignments': {}, 'annotation_counts': {}}


def save_assignments(data):
    with open(ASSIGNMENTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def assign_rows(prolific_id, df, assignments):
    if prolific_id in assignments['assignments']:
        return assignments['assignments'][prolific_id]

    already_done = get_annotated_row_ids(prolific_id, df.columns)
    counts = assignments['annotation_counts']

    eligible = [
        (i, counts.get(str(i), 0))
        for i in range(len(df))
        if str(i) not in already_done and counts.get(str(i), 0) < ANNOTATIONS_PER_ROW
    ]
    eligible.sort(key=lambda x: -x[1])  # fill rows closest to 3 first
    assigned = [i for i, _ in eligible[:ROWS_PER_ANNOTATOR]]

    assignments['assignments'][prolific_id] = assigned
    save_assignments(assignments)
    return assigned


def get_pending(prolific_id, assigned, df):
    done = get_annotated_row_ids(prolific_id, df.columns)
    return [i for i in assigned if str(i) not in done]


def main():
    st.title("Misinformation Domain Annotation Tool")

    prolific_id = get_prolific_id()
    if not prolific_id:
        st.error("No Prolific ID found in URL. Please access this page via your Prolific study link.")
        st.caption("Expected URL format: `http://localhost:8501/?PROLIFIC_PID=abc123`")
        prolific_id = st.text_input("Or enter your Prolific ID manually for testing:")
        if not prolific_id:
            return

    st.sidebar.markdown(f"**Prolific ID:** `{prolific_id}`")

    csv_path = st.sidebar.text_input("CSV file path", value="data.csv")
    if not os.path.exists(csv_path):
        st.warning(f"CSV not found at `{csv_path}`.")
        return

    df, text_col = load_df(csv_path)
    if text_col is None:
        st.error("No text column found. Expected one of: text, note, message, content, post")
        st.write("Available columns:", df.columns.tolist())
        return

    assignments = load_assignments()
    assigned = assign_rows(prolific_id, df, assignments)
    pending = get_pending(prolific_id, assigned, df)

    st.sidebar.markdown(f"**Assigned:** {len(assigned)} rows")
    st.sidebar.markdown(f"**Remaining:** {len(pending)} rows")

    if not pending:
        st.success("You have completed all your assigned items. Thank you!")
        st.balloons()
        return

    for key, default in [('local_idx', 0), ('domain', None), ('subcategory', None)]:
        if key not in st.session_state:
            st.session_state[key] = default

    if st.session_state.local_idx >= len(pending):
        st.session_state.local_idx = len(pending) - 1

    row_idx = pending[st.session_state.local_idx]
    orig_row = df.iloc[row_idx].to_dict()
    current_text = orig_row[text_col]

    done_count = len(assigned) - len(pending) + st.session_state.local_idx
    st.write(f"**Item {done_count + 1} of {len(assigned)}**")
    st.progress((done_count + 1) / len(assigned))

    st.subheader("Text to annotate:")
    st.info(current_text)

    # Step 1: Domain
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

    # Step 2: Subcategory
    if st.session_state.domain == 'politics':
        st.subheader("Step 2 — Politics Subcategory")
        for tag, label, description in POLITICS_SUBCATEGORIES:
            is_selected = st.session_state.subcategory == tag
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button(f"✅ {label}" if is_selected else label, key=f"sub_{tag}", use_container_width=True):
                    st.session_state.subcategory = None if is_selected else tag
                    st.rerun()
            with col2:
                st.caption(description)

    elif st.session_state.domain == 'finance':
        st.subheader("Step 2 — Finance Subcategory")
        for tag, label, _ in FINANCE_SUBCATEGORIES:
            is_selected = st.session_state.subcategory == tag
            if st.button(f"✅ {label}" if is_selected else label, key=f"sub_{tag}", use_container_width=True):
                st.session_state.subcategory = None if is_selected else tag
                st.rerun()

    if st.session_state.domain:
        st.success(f"Selected: **{st.session_state.domain.title()}** / **{st.session_state.subcategory or '—'}**")

    # Navigation
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
            save_annotation(prolific_id, row_idx, orig_row,
                            st.session_state.domain, st.session_state.subcategory)
            # Update annotation count
            assignments['annotation_counts'][str(row_idx)] = \
                assignments['annotation_counts'].get(str(row_idx), 0) + 1
            save_assignments(assignments)
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


if __name__ == "__main__":
    main()
