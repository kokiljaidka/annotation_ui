import pandas as pd
import streamlit as st
import json
from collections import Counter
import os
import ast

# Load the data
@st.cache_data
def load_data():
    df = pd.read_csv('/Users/svetachurina/work/code mixing/clean_code_mix_sample.csv')
    return df

# Load existing tags from tagged_text column
@st.cache_data
def get_existing_tags(df):
    tags = set()
    if 'tagged_text' in df.columns:
        for tagged_text in df['tagged_text'].dropna():
            try:
                if isinstance(tagged_text, str):
                    # Try to parse as literal eval first
                    try:
                        parsed = ast.literal_eval(tagged_text)
                        if isinstance(parsed, list):
                            for item in parsed:
                                if isinstance(item, tuple) and len(item) >= 2:
                                    tags.add(item[1])
                    except:
                        # If that fails, try to extract tags from string format
                        # Look for patterns like (word, tag) or word -> tag
                        import re
                        # Pattern for (word, tag) format
                        pattern1 = r'\([^,]+,\s*([^)]+)\)'
                        matches1 = re.findall(pattern1, tagged_text)
                        tags.update(matches1)
                        
                        # Pattern for word -> tag format
                        pattern2 = r'→\s*([^\s,]+)'
                        matches2 = re.findall(pattern2, tagged_text)
                        tags.update(matches2)
            except Exception as e:
                pass
    
    # Add some common tags if none found
    if not tags:
        tags = {'english', 'hokkien', 'mandarin', 'malay', 'tamil', 'pronoun', 'punctuation'}
    
    return sorted(list(tags))

# Parse messages from the final_message_list column
def parse_messages(messages_str):
    """Parse messages from string format to list"""
    try:
        # Try to parse as literal eval
        if isinstance(messages_str, str):
            parsed = ast.literal_eval(messages_str)
            if isinstance(parsed, list):
                return parsed
    except:
        pass
    
    # If parsing fails, return as single message
    return [messages_str] if messages_str else []

# Save annotations
def save_annotations(annotations, filename='annotations.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(annotations, f, ensure_ascii=False, indent=2)

# Load annotations
def load_annotations(filename='annotations.json'):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Main Streamlit app
def main():
    st.title("Code-Mixing Annotation Tool")
    
    # Load data
    df = load_data()
    
    if 'final_message_list' not in df.columns:
        st.error("Column 'final_message_list' not found in the CSV file!")
        st.write("Available columns:", list(df.columns))
        return
    
    # Get existing tags
    existing_tags = get_existing_tags(df)
    
    # Load existing annotations
    annotations = load_annotations()
    
    # Initialize session state
    if 'current_message_idx' not in st.session_state:
        st.session_state.current_message_idx = 0
    if 'current_word_idx' not in st.session_state:
        st.session_state.current_word_idx = 0
    if 'annotations' not in st.session_state:
        st.session_state.annotations = annotations
    if 'selected_tag' not in st.session_state:
        st.session_state.selected_tag = None
    
    # Parse all messages from the dataframe
    all_messages = []
    for idx, row in df.iterrows():
        messages_str = row['final_message_list']
        if pd.notna(messages_str):
            parsed_messages = parse_messages(messages_str)
            all_messages.extend(parsed_messages)
    
    if not all_messages:
        st.error("No messages found in 'final_message_list' column!")
        return
    
    if st.session_state.current_message_idx >= len(all_messages):
        st.success("All messages have been annotated!")
        return
    
    current_message = all_messages[st.session_state.current_message_idx]
    
    # Display progress
    st.write(f"Message {st.session_state.current_message_idx + 1} of {len(all_messages)}")
    progress_bar = (st.session_state.current_message_idx + 1) / len(all_messages)
    st.progress(progress_bar)
    
    # Display current message
    st.subheader("Current Message:")
    st.write(f"**{current_message}**")
    
    # Split message into words
    words = current_message.split()
    
    if st.session_state.current_word_idx >= len(words):
        st.success("All words in this message have been annotated!")
        st.button("Next Message", on_click=lambda: setattr(st.session_state, 'current_message_idx', st.session_state.current_message_idx + 1) or setattr(st.session_state, 'current_word_idx', 0))
        return
    
    current_word = words[st.session_state.current_word_idx]
    
    # Display current word
    st.subheader(f"Annotating word {st.session_state.current_word_idx + 1} of {len(words)}:")
    st.write(f"**Word:** {current_word}")
    
    # Language buttons
    st.subheader("Select Language Tag:")
    
    # Define the language buttons
    languages = [
        ('english', 'English'),
        ('hokkien', 'Hokkien'),
        ('malay', 'Malay'),
        ('mandarin', 'Mandarin'),
        ('pronoun', 'Pronoun'),
        ('punctuation', 'Punctuation'),
        ('tamil', 'Tamil')
    ]
    
    # Create buttons in a grid layout
    cols = st.columns(4)
    
    for i, (tag, label) in enumerate(languages):
        col_idx = i % 4
        with cols[col_idx]:
            # Use different button styles based on selection
            if st.session_state.selected_tag == tag:
                if st.button(f"✅ {label}", key=f"btn_{tag}_{st.session_state.current_message_idx}_{st.session_state.current_word_idx}"):
                    st.session_state.selected_tag = None
                    st.rerun()
            else:
                if st.button(label, key=f"btn_{tag}_{st.session_state.current_message_idx}_{st.session_state.current_word_idx}"):
                    st.session_state.selected_tag = tag
                    st.rerun()
    
    # Custom tag input
    st.subheader("Or enter custom tag:")
    custom_tag = st.text_input(
        "Custom tag:",
        key=f"custom_{st.session_state.current_message_idx}_{st.session_state.current_word_idx}",
        on_change=lambda: setattr(st.session_state, 'selected_tag', None)
    )
    
    # Determine final tag
    final_tag = custom_tag if custom_tag else st.session_state.selected_tag
    
    # Word-level navigation buttons
    st.subheader("Word Navigation:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⬅️ Previous Word") and st.session_state.current_word_idx > 0:
            st.session_state.current_word_idx -= 1
            st.session_state.selected_tag = None
            st.rerun()
    
    with col2:
        if st.button("💾 Save & Next Word"):
            if final_tag:
                # Save annotation
                message_key = f"message_{st.session_state.current_message_idx}"
                if message_key not in st.session_state.annotations:
                    st.session_state.annotations[message_key] = {
                        'message': current_message,
                        'annotations': []
                    }
                
                # Update or add annotation
                word_annotations = st.session_state.annotations[message_key]['annotations']
                if st.session_state.current_word_idx < len(word_annotations):
                    word_annotations[st.session_state.current_word_idx] = (current_word, final_tag)
                else:
                    word_annotations.append((current_word, final_tag))
                
                # Save to file
                save_annotations(st.session_state.annotations)
                
                # Move to next word
                st.session_state.current_word_idx += 1
                st.session_state.selected_tag = None
                st.rerun()
            else:
                st.error("Please select a language tag or enter a custom tag!")
    
    with col3:
        if st.button("➡️ Next Word") and st.session_state.current_word_idx < len(words) - 1:
            st.session_state.current_word_idx += 1
            st.session_state.selected_tag = None
            st.rerun()
    
    # Message-level navigation buttons
    st.subheader("Message Navigation:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⬅️ Previous Message") and st.session_state.current_message_idx > 0:
            st.session_state.current_message_idx -= 1
            st.session_state.current_word_idx = 0
            st.session_state.selected_tag = None
            st.rerun()
    
    with col2:
        st.write("")  # Empty space for centering
    
    with col3:
        if st.button("➡️ Next Message") and st.session_state.current_message_idx < len(all_messages) - 1:
            st.session_state.current_message_idx += 1
            st.session_state.current_word_idx = 0
            st.session_state.selected_tag = None
            st.rerun()
    
    # Keyboard shortcuts info
    st.info("💡 **Tip:** Press Enter in the custom tag field to save and move to next word")
    
    # Display current annotations for this message
    st.subheader("Current Annotations for this Message:")
    message_key = f"message_{st.session_state.current_message_idx}"
    if message_key in st.session_state.annotations:
        annotations_list = st.session_state.annotations[message_key]['annotations']
        for i, (word, tag) in enumerate(annotations_list):
            if i == st.session_state.current_word_idx:
                st.write(f"**{i+1}. {word} → {tag}** (current)")
            else:
                st.write(f"{i+1}. {word} → {tag}")
    
    # Export functionality
    st.subheader("Export Annotations")
    if st.button("📥 Export to CSV"):
        export_data = []
        for message_key, data in st.session_state.annotations.items():
            message = data['message']
            annotations = data['annotations']
            tagged_text = str(annotations)  # Convert to string format
            export_data.append({
                'message': message,
                'tagged_text': tagged_text
            })
        
        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="annotated_code_mixing.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
