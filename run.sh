set -e

mkdir -p teams

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Starting Streamlit app..."
streamlit run app/app.py