# Jarvis AI Assistant v2.0 🤖

A comprehensive, production-ready AI assistant with advanced capabilities including voice processing, document analysis, image generation, scheduling, and multi-platform messaging support.

## 🚀 Features

### 🧠 Core AI Capabilities
- **Multi-LLM Support**: Google Gemini & OpenAI GPT integration
- **Semantic Search**: Advanced document search with Sentence Transformers
- **Voice Processing**: OpenAI Whisper for speech-to-text
- **Image Generation**: DALL-E integration for AI image creation
- **Document Analysis**: PDF, DOCX, TXT processing with Q&A

### 🌐 Real-time Information
- Weather information for any location
- Latest news by category (tech, business, world, etc.)
- Cryptocurrency prices and market data
- Web search and content scraping
- Multi-language translation

### 🔧 Advanced Tools
- **Calculator**: Complex mathematical expressions, trigonometry
- **Unit Converter**: Length, weight, temperature, volume
- **Task Scheduler**: Smart reminders with repeat patterns
- **Media Downloader**: YouTube video/audio extraction
- **Image Processor**: Analysis, resizing, format conversion

### 📱 Multi-Platform Support
- **Telegram**: Full bot integration with webhooks
- **WhatsApp**: Business API integration (Meta)
- **Web API**: RESTful endpoints for all features

### 🗄️ Data Management
- **SQLite Database**: User data, conversations, documents
- **Knowledge Base**: Persistent document storage with embeddings
- **Analytics**: Usage tracking and statistics
- **Session Management**: Context-aware conversations

## 🏗️ Architecture

### Core Components
```
├── app.py                 # Main Flask application
├── core/
│   ├── database.py        # SQLite database manager
│   ├── ai_engine.py       # AI/ML processing engine
│   ├── message_router.py  # Central message routing
│   ├── scheduler.py       # APScheduler for reminders
│   ├── assistant.py       # Legacy assistant (enhanced)
│   ├── web_tools.py       # Web scraping & APIs
│   └── advanced_features.py # Calculators & utilities
├── integrations/
│   ├── telegram_webhook.py   # Telegram webhook handler
│   ├── whatsapp_webhook.py  # WhatsApp webhook handler
│   └── telegram.py          # Legacy polling bot
└── data/
    ├── jarvis.db           # SQLite database
    ├── documents/          # Uploaded files
    └── knowledge_base/     # PDF knowledge base
```

### Technology Stack
- **Backend**: Flask, SQLite, APScheduler
- **AI/ML**: Google Gemini, OpenAI, Sentence Transformers, Whisper
- **Messaging**: Telegram Bot API, WhatsApp Business API
- **Processing**: PyMuPDF, Pillow, OpenCV, PyTube
- **Deployment**: Gunicorn, Render

## 📦 Installation

### Prerequisites
- Python 3.11+
- Git

### Local Development
```bash
# Clone repository
git clone <repository-url>
cd jarvis-bot

# Install dependencies
pip install -r requirements_new.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys

# Run locally
python app.py
```

### Environment Variables
```bash
# AI APIs
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_token

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_verify_token

# Configuration
BOT_NAME=Jarvis
DEBUG_MODE=False
PORT=5000
```

## 🚀 Deployment

### Render Deployment
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Use the provided `render.yaml` configuration
4. Set environment variables in Render dashboard
5. Deploy!

### Manual Deployment
```bash
# Using Gunicorn
gunicorn app:create_app --bind 0.0.0.0:5000

# Using Docker (create Dockerfile)
docker build -t jarvis-bot .
docker run -p 5000:5000 jarvis-bot
```

## 🔧 API Endpoints

### Health & Status
- `GET /` - Health check
- `GET /api/stats` - Application statistics

### Webhooks
- `POST /webhook/telegram` - Telegram webhook
- `GET|POST /webhook/whatsapp` - WhatsApp webhook

### Data Management
- `GET /api/conversations` - Get user conversations
- `POST /api/knowledge-base` - Upload documents
- `GET|POST /api/reminders` - Manage reminders

## 💬 Usage Examples

### Text Commands
```
# Weather
"Weather in New York"
"What's the weather like in London?"

# News
"Latest technology news"
"Show me business headlines"

# Calculations
"Calculate 15% of 250"
"What's the square root of 144?"
"Convert 100 km to miles"

# Scheduling
"Remind me to call John tomorrow at 2 PM"
"Schedule a meeting for next Friday at 10 AM"

# Information
"Search for artificial intelligence trends"
"Bitcoin price"
"Translate 'hello world' to Spanish"

# Document Analysis
Upload a PDF and ask: "Summarize this document"
"What does this document say about AI?"
```

### Voice Commands
Send voice messages for:
- Natural conversation
- Hands-free operation
- Complex queries

### Document Upload
- PDF analysis and Q&A
- Image processing and analysis
- Knowledge base integration

## 🛠️ Development

### Adding New Features
1. Create feature module in `core/`
2. Add to `AIEngine` or `MessageRouter`
3. Update webhook handlers
4. Test with both platforms

### Database Schema
```sql
-- Users table
users (id, platform_id, platform, username, preferences, created_at)

-- Conversations
conversations (id, user_id, message_type, user_message, bot_response, created_at)

-- Documents
documents (id, user_id, filename, file_path, embeddings, created_at)

-- Reminders
reminders (id, user_id, title, reminder_time, repeat_pattern, is_active)
```

### Testing
```bash
# Test individual components
python -m pytest tests/

# Test webhooks locally
ngrok http 5000
# Update webhook URLs in platform settings
```

## 📊 Monitoring

### UptimeRobot Setup
1. Create account at uptimerobot.com
2. Add HTTP monitor for your Render URL
3. Set check interval to 5 minutes
4. Configure alerts (email, SMS, Slack)

### Logs & Analytics
- Application logs via Render dashboard
- User analytics in SQLite database
- Performance metrics via `/api/stats`

## 🔒 Security

- Environment variables for sensitive data
- Input validation and sanitization
- Rate limiting (implement as needed)
- Webhook verification tokens
- HTTPS enforcement in production

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- Check logs in Render dashboard
- Review webhook delivery in platform settings
- Test individual components locally
- Monitor database for errors

---

**Jarvis v2.0** - Your intelligent AI assistant, now with production-grade architecture! 🚀
