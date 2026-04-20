import pandas as pd
import streamlit as st
import json
import os

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


@st.cache_data
def load_data(csv_path):
    df = pd.read_csv(csv_path)
    return df


def save_annotations(annotations, filename='annotations.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(annotations, f, ensure_ascii=False, indent=2)


def load_annotations(filename='annotations.json'):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def render_subcategory_buttons(subcategories, key_prefix, current_selection):
    selected = current_selection
    cols = st.columns(2)
    for i, (tag, label, description) in enumerate(subcategories):
        with cols[i % 2]:
            is_selected = selected == tag
            btn_label = f"✅ {label}" if is_selected else label
            if description:
                st.caption(description)
            if st.button(btn_label, key=f"{key_prefix}_{tag}", use_container_width=True):
                selected = None if is_selected else tag
                st.rerun()
    return selected


def main():
    st.title("Misinformation Domain Annotation Tool")

    # Sidebar: CSV upload
    st.sidebar.header("Data Source")
    csv_path = st.sidebar.text_input("CSV file path", value="data.csv")

    if not os.path.exists(csv_path):
        st.warning(f"CSV not found at `{csv_path}`. Please enter a valid path in the sidebar.")
        return

    df = load_data(csv_path)

    # Detect text column
    text_col_candidates = ['text', 'note', 'message', 'content', 'post']
    text_col = next((c for c in text_col_candidates if c in df.columns), None)
    if text_col is None:
        st.error(f"No text column found. Expected one of: {text_col_candidates}")
        st.write("Available columns:", list(df.columns))
        return

    texts = df[text_col].dropna().tolist()
    row_ids = df[df[text_col].notna()].index.tolist()

    # Session state init
    for key, default in [
        ('idx', 0),
        ('domain', None),
        ('subcategory', None),
        ('annotations', load_annotations()),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    annotations = st.session_state.annotations

    if st.session_state.idx >= len(texts):
        st.success("All items have been annotated!")
        _render_export(annotations)
        return

    idx = st.session_state.idx
    row_id = str(row_ids[idx])
    current_text = texts[idx]

    # Progress
    st.write(f"**Item {idx + 1} of {len(texts)}**")
    st.progress((idx + 1) / len(texts))

    # Restore existing annotation for this item
    if row_id in annotations and st.session_state.domain is None:
        st.session_state.domain = annotations[row_id].get('domain')
        st.session_state.subcategory = annotations[row_id].get('subcategory')

    # Display text
    st.subheader("Text to annotate:")
    st.info(current_text)

    # Step 1: Domain
    st.subheader("Step 1 — Select Domain")
    col_pol, col_fin = st.columns(2)
    with col_pol:
        pol_label = "✅ Politics" if st.session_state.domain == 'politics' else "Politics"
        if st.button(pol_label, key="domain_politics", use_container_width=True):
            st.session_state.domain = None if st.session_state.domain == 'politics' else 'politics'
            st.session_state.subcategory = None
            st.rerun()
    with col_fin:
        fin_label = "✅ Finance" if st.session_state.domain == 'finance' else "Finance"
        if st.button(fin_label, key="domain_finance", use_container_width=True):
            st.session_state.domain = None if st.session_state.domain == 'finance' else 'finance'
            st.session_state.subcategory = None
            st.rerun()

    # Step 2: Subcategory (conditional)
    if st.session_state.domain == 'politics':
        st.subheader("Step 2 — Politics Subcategory")
        for tag, label, description in POLITICS_SUBCATEGORIES:
            is_selected = st.session_state.subcategory == tag
            btn_label = f"✅ {label}" if is_selected else label
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button(btn_label, key=f"sub_{tag}_{idx}", use_container_width=True):
                    st.session_state.subcategory = None if is_selected else tag
                    st.rerun()
            with col2:
                st.caption(description)

    elif st.session_state.domain == 'finance':
        st.subheader("Step 2 — Finance Subcategory")
        for tag, label, _ in FINANCE_SUBCATEGORIES:
            is_selected = st.session_state.subcategory == tag
            btn_label = f"✅ {label}" if is_selected else label
            if st.button(btn_label, key=f"sub_{tag}_{idx}", use_container_width=True):
                st.session_state.subcategory = None if is_selected else tag
                st.rerun()

    # Save & navigate
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Previous", disabled=idx == 0):
            st.session_state.idx -= 1
            st.session_state.domain = None
            st.session_state.subcategory = None
            st.rerun()

    with col2:
        can_save = st.session_state.domain is not None and st.session_state.subcategory is not None
        if st.button("💾 Save & Next", disabled=not can_save, type="primary"):
            annotations[row_id] = {
                'row_id': row_id,
                'text': current_text,
                'domain': st.session_state.domain,
                'subcategory': st.session_state.subcategory,
            }
            st.session_state.annotations = annotations
            save_annotations(annotations)
            st.session_state.idx += 1
            st.session_state.domain = None
            st.session_state.subcategory = None
            st.rerun()

    with col3:
        if st.button("Skip ➡️", disabled=idx >= len(texts) - 1):
            st.session_state.idx += 1
            st.session_state.domain = None
            st.session_state.subcategory = None
            st.rerun()

    if not can_save:
        st.caption("Select both a domain and subcategory to enable Save.")

    # Show current selection summary
    if st.session_state.domain:
        sub_label = st.session_state.subcategory or "—"
        st.success(f"Current selection: **{st.session_state.domain.title()}** / **{sub_label}**")

    st.divider()
    _render_export(annotations)


def _render_export(annotations):
    st.subheader("Export Annotations")
    annotated_count = len(annotations)
    st.write(f"{annotated_count} item(s) annotated.")
    if annotated_count > 0 and st.button("📥 Export to CSV"):
        rows = list(annotations.values())
        export_df = pd.DataFrame(rows)
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="annotated_misinformation.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
