# 🤖 Jarvis Bot - AI Assistant

A powerful AI assistant bot that can be deployed on multiple messaging platforms (Telegram and WhatsApp). Jarvis can process text messages, voice notes, and PDF documents while maintaining a knowledge base for enhanced responses.

## ✨ Features

- **Multi-Platform Support**: Telegram (ready) and WhatsApp (placeholder)
- **Voice Processing**: Convert voice messages to text and respond with audio
- **Document Analysis**: Upload PDF documents to expand Jarvis's knowledge base
- **AI-Powered Responses**: Uses OpenAI's GPT models for intelligent conversations
- **Modular Architecture**: Easy to extend and maintain

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

1. Copy `.env` file and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ```

2. Get your API keys:
   - **OpenAI API Key**: Visit [OpenAI Platform](https://platform.openai.com/api-keys)
   - **Telegram Bot Token**: Message [@BotFather](https://t.me/BotFather) on Telegram

### 3. Create Telegram Bot

1. Start a chat with [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Choose a name and username for your bot
4. Copy the provided token to your `.env` file

### 4. Run the Bot

```bash
python main.py --platform telegram
```

### 5. Test Your Bot

- Find your bot on Telegram
- Send `/start` to begin
- Try text messages, voice notes, and PDF uploads!

## 📁 Project Structure

```
Jarvis Bot/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (API keys)
├── README.md              # This file
├── core/
│   ├── assistant.py       # Core AI logic
│   └── utils.py          # Helper functions (PDF, TTS)
├── integrations/
│   ├── telegram.py       # Telegram bot implementation
│   └── whatsapp.py      # WhatsApp placeholder
└── data/
    └── knowledge_base/   # PDF documents storage
```

## 🎯 Available Commands

### Bot Commands (Telegram)

- `/start` - Welcome message and overview
- `/help` - Detailed help information
- `/status` - Check bot system status
- `/voice_on` - Enable voice responses
- `/voice_off` - Disable voice responses

### CLI Commands

```bash
# Run Telegram bot (default)
python main.py

# Run specific platform
python main.py --platform telegram
python main.py --platform whatsapp

# Utility commands
python main.py --setup          # Show setup instructions
python main.py --check-env      # Verify environment
python main.py --validate-keys  # Test API keys
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI functionality | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather | Yes (for Telegram) |
| `WHATSAPP_API_KEY` | WhatsApp API key | No (future use) |
| `BOT_NAME` | Custom bot name | No |
| `DEBUG_MODE` | Enable debug logging | No |

### Customization

You can customize the bot behavior by modifying:

- **AI Responses**: Edit `core/assistant.py` to change AI behavior
- **Voice Settings**: Modify TTS parameters in `core/utils.py`
- **Commands**: Add new commands in `integrations/telegram.py`

## 📚 Usage Examples

### Text Conversations
```
User: "What's the weather like?"
Jarvis: "I'd be happy to help with weather information! However, I don't currently have access to real-time weather data..."
```

### Voice Messages
1. Send a voice note to the bot
2. Jarvis will transcribe your speech
3. Process your request and respond
4. Optionally reply with voice (if enabled)

### Document Upload
1. Send a PDF file to the bot
2. Jarvis adds it to the knowledge base
3. Ask questions about the document content
4. Get informed responses based on the document

## 🛠️ Development

### Adding New Features

1. **New Commands**: Add handlers in `integrations/telegram.py`
2. **AI Capabilities**: Extend `core/assistant.py`
3. **Utilities**: Add helper functions to `core/utils.py`

### Testing

```bash
# Check environment
python main.py --check-env

# Validate API keys
python main.py --validate-keys

# Run with debug logging
DEBUG_MODE=True python main.py
```

## 🔮 Future Enhancements

### Phase 2 - WhatsApp Integration
- Complete WhatsApp Business API integration
- Webhook server implementation
- Message handling for WhatsApp

### Phase 3 - Advanced Features
- Vector search for knowledge base
- Multi-language support
- Integration with external APIs
- Advanced voice processing
- Image analysis capabilities

## 🐛 Troubleshooting

### Common Issues

1. **"TELEGRAM_BOT_TOKEN not found"**
   - Check your `.env` file
   - Ensure the token is correct from BotFather

2. **"OpenAI API key validation failed"**
   - Verify your OpenAI API key
   - Check your account has sufficient credits

3. **Voice messages not working**
   - Ensure `pydub` and `speechrecognition` are installed
   - Check microphone permissions

4. **PDF processing fails**
   - Verify the file is a valid PDF
   - Check file size limits

### Getting Help

- Check the logs in `jarvis_bot.log`
- Use `python main.py --check-env` to verify setup
- Review error messages for specific issues

## 📄 License

This project is open source. Feel free to modify and distribute according to your needs.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

**Happy chatting with Jarvis! 🚀**
