# Annotation Platform for Code-mix text 
A lightweight annotation tool for labeling text data at the message and word level.  
Designed for efficient manual annotation workflows, especially for code-mixing and linguistic analysis tasks.

## Setup 
1. **Clone the repository**
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Update dataset path
In the main script (around line 11), update the file path to your dataset:
```python
df = pd.read_csv('/path/to/your/file.csv')
```
4. Make the run script executable
```bash
chmod +x run_app.sh
```
5. Run the application
```bash
./run_app.sh
```

## Usage
Open your browser at:
http://localhost:8501/
The interface will:

	•	Display text message by message
	
	•	Allow annotation word by word
After completing annotations use the Save button to export results as a CSV file

Notes:

	•	The platform is designed for local use
	
	•	Input data must be in CSV format
