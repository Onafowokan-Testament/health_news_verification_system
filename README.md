"""
# 🏥 Nigerian Health Misinformation Detection System

A production-ready RAG (Retrieval-Augmented Generation) agent that helps older adults in Nigeria verify health claims using curated medical knowledge and PubMed research.

## 🌟 Features

✅ **Curated Nigerian Health Myths** - 15+ pre-loaded dangerous myths  
✅ **Real-time PubMed Search** - Access to 30M+ medical research papers  
✅ **Confidence Scoring** - Every answer includes a confidence percentage  
✅ **Source Citations** - References WHO, NCDC, and peer-reviewed journals  
✅ **Multi-language Support** - English, Pidgin, Yoruba, Hausa, Igbo  
✅ **Voice Output** - Text-to-speech for accessibility  
✅ **Streamlit UI** - Beautiful, user-friendly interface  
✅ **Vector Search** - Fast semantic search using Chroma DB  
✅ **Production Ready** - Error handling, logging, rate limiting  

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9 or higher
- OpenAI API key
- Email address (for PubMed API)

### 2. Installation

```bash
# Clone or download the project
cd nigerian-health-checker

# Run setup script
python setup.py

# Edit .env file with your API keys
nano .env  # or use any text editor
```

### 3. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
nigerian-health-checker/
├── config.py              # Configuration and settings
├── data_loader.py         # Curated health myths database
├── pubmed_search.py       # PubMed API integration
├── vector_store.py        # Chroma vector database manager
├── agent.py               # RAG agent implementation
├── app.py                 # Streamlit user interface
├── requirements.txt       # Python dependencies
├── setup.py              # Setup script
├── .env.example          # Environment variables template
├── .env                  # Your API keys (create this)
└── data/
    └── chroma_db/        # Vector database storage
```

## 🔧 Configuration

Edit `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here
PUBMED_EMAIL=your-email@example.com

# Optional
LANGSMITH_API_KEY=your-langsmith-key  # For debugging
OPENAI_MODEL=gpt-4o                   # Model to use
```

## 📊 How It Works

### Architecture

```
User Query
    ↓
[Streamlit UI]
    ↓
[RAG Agent]
    ↓
├─→ [Curated Myths Vector DB] ─→ Quick answers for known myths
│
└─→ [PubMed API] ─→ Research for unknown claims
    ↓
[OpenAI GPT-4o]
    ↓
[Response with Verdict + Confidence + Sources]
    ↓
[Text-to-Speech Output]
```

### Search Strategy

1. **Check Curated Database First** - Fast answers for common Nigerian myths
2. **Search PubMed if Needed** - Access latest medical research
3. **Combine Evidence** - Synthesize information from multiple sources
4. **Provide Verdict** - TRUE, FALSE, PARTIALLY TRUE, or UNCLEAR
5. **Explain Clearly** - Simple language suitable for older adults

## 🧪 Testing

Try these example claims:

- "Does hot water cure malaria?"
- "Can sugar cause diabetes?"
- "Do antibiotics cure viral infections?"
- "Does bitter kola cure COVID-19?"
- "Can saltwater cure Ebola?"

## 📝 Adding New Health Myths

Edit `data_loader.py` and add to `CURATED_HEALTH_MYTHS`:

```python
{
    "claim": "Your new health claim here",
    "verdict": "FALSE",
    "confidence": 95,
    "explanation": "Clear explanation here",
    "sources": [
        "WHO Guidelines",
        "NCDC Nigeria"
    ],
    "category": "category_name",
    "language": "en"
}
```

Then restart the app to re-index.

## 🌍 Language Support

Currently supports:
- **English** - Full support
- **Pidgin** - Uses English TTS
- **Yoruba** - Limited TTS support
- **Hausa** - Limited TTS support
- **Igbo** - Limited TTS support

To improve language support, consider:
- Using Google Translate API for translation
- Translating curated myths into local languages
- Using multilingual embeddings

## 🔒 Security & Privacy

- API keys stored in `.env` (never commit to Git!)
- No user data stored or logged
- All processing happens in real-time
- PubMed searches are anonymous

## 💰 Cost Estimates

**Per Query:**
- OpenAI API: $0.01 - $0.05
- PubMed API: Free
- Vector Search: Free

**Monthly (1000 queries):**
- ~$10-50 depending on query complexity

## 🐛 Troubleshooting

### "OPENAI_API_KEY not found"
- Make sure you created `.env` file
- Copy from `.env.example` and add your key

### "PubMed search failed"
- Check your email is set in `.env`
- PubMed rate limits to 3 requests/second
- Wait a moment and try again

### "No module named 'streamlit'"
- Run: `pip install -r requirements.txt`

### Vector database errors
- Delete `data/chroma_db/` folder
- Restart app to re-index

## 🚀 Deployment Options

### Option 1: Streamlit Cloud (Free)
1. Push code to GitHub
2. Go to share.streamlit.io
3. Connect your repo
4. Add secrets (API keys) in dashboard

### Option 2: Railway (Easy)
1. Connect GitHub repo
2. Add environment variables
3. Deploy with one click

### Option 3: AWS/GCP/Azure
- Use Docker container
- Deploy to EC2/Compute Engine/VM
- Set up HTTPS and domain

## 📈 Future Improvements

- [ ] Add voice input (speech-to-text)
- [ ] Translate myths to local languages
- [ ] Add SMS interface for feature phones
- [ ] Create WhatsApp bot
- [ ] Add offline mode with cached responses
- [ ] Build mobile app (Flutter/React Native)
- [ ] Add community reporting of new myths
- [ ] Integration with Nigerian health clinics

## 🤝 Contributing

To add more health myths:
1. Research the claim thoroughly
2. Find authoritative sources (WHO, NCDC, peer-reviewed papers)
3. Add to `data_loader.py`
4. Test with the system
5. Submit pull request

## 📄 License

MIT License - Feel free to use and modify for your projects

## 🙏 Acknowledgments

- WHO for public health guidelines
- NCDC Nigeria for local health information
- PubMed/NCBI for medical research access
- LangChain team for RAG framework
- Anthropic for Claude (used in development)

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Email: your-email@example.com

## ⚠️ Disclaimer

This system is for informational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified health providers with any questions regarding medical conditions.

---

Built with ❤️ for Nigerian healthcare
"""