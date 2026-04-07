# Trading Bot for Beginners

Hi! This is a simple guide to use the trading bot. It's like having a robot that helps you buy and sell stocks. Don't worry if you don't know coding - this guide explains everything step by step.

## What Does This Bot Do?

The bot is like a smart helper that:
- Waits for signals from TradingView (like a stock chart app)
- Reads news about stocks to see if people are happy or sad about them
- Decides if it should buy, sell, or wait
- Places orders on Alpaca (like a stock trading app)

## What You Need First

You need these things before starting:
1. **Alpaca account** - This is like a bank for stocks. Start with "paper trading" (fake money) first!
2. **NewsAPI key** - This lets the bot read news. It's free.
3. **TradingView account** - This sends signals to the bot. Free version works.
4. **Python** - This is already on your computer if you have Windows.

## Step 1: Get Your Secret Codes (API Keys)

The bot needs special codes to talk to other websites. Think of them like passwords.

### How to Get Alpaca Codes:
1. Go to [alpaca.markets](https://alpaca.markets) and make a free account
2. Click "Paper Trading" (this uses fake money - safe to learn!)
3. Go to your account settings
4. Find "API Keys" section
5. Click "Generate New Key"
6. Copy the API Key and Secret Key - save them somewhere safe!

### How to Get NewsAPI Key:
1. Go to [newsapi.org](https://newsapi.org)
2. Click "Get API Key" (it's free!)
3. Make an account
4. Copy your API key

### How to Set Up TradingView:
1. Go to [tradingview.com](https://tradingview.com)
2. Make a free account
3. You'll use this later to send signals

### Put All Codes in One File:
1. In the bot folder, find a file called `.env.example`
2. Right-click it and choose "Copy"
3. Right-click in the same folder and choose "Paste" - it will make `.env.example - Copy`
4. Rename the copy to just `.env` (remove the " - Copy" part)
5. Right-click `.env` and choose "Open with Notepad"
6. You'll see lines like this:
   ```
   ALPACA_API_KEY=your_alpaca_key_here
   ALPACA_SECRET_KEY=your_alpaca_secret_here
   ALPACA_BASE_URL=https://paper-api.alpaca.markets
   NEWS_API_KEY=your_newsapi_key_here
   WEBHOOK_SECRET=my_secret_token
   ```
7. Replace the words after the `=` with your real codes:
   - `your_alpaca_key_here` → paste your Alpaca API Key
   - `your_alpaca_secret_here` → paste your Alpaca Secret Key
   - `your_newsapi_key_here` → paste your NewsAPI key
   - Leave the other lines as they are
8. Save the file and close Notepad

## Step 2: Start the Bot

Just double-click the `start.bat` file in the bot folder.

It will:
- Check if your codes are set up
- Get everything ready (this takes longer the first time)
- Start the bot and show "Trading bot started"

## Step 3: Send a Test Signal

Now you need to tell the bot what to do. Use TradingView to send a message.

### Set Up TradingView Alert:
1. Go to TradingView in your web browser
2. Search for a stock like "AAPL" (Apple)
3. Click the "Alert" button (bell icon)
4. In "Message" box, paste this exactly:
   ```json
   {
     "secret": "my_secret_token",
     "symbol": "{{ticker}}",
     "action": "BUY",
     "price": {{close}},
     "indicators": {
       "rsi": 32.5,
       "macd": "bullish"
     }
   }
   ```
5. In "Webhook URL" box, put: `http://localhost:8000/webhook`
6. Click "Create" to save the alert

### Test It:
1. Change the stock price a little in TradingView
2. The alert should trigger and send a message to your bot
3. Check the bot window - it should show it received the signal

## Step 4: Check What Happened

The bot will tell you what it decided:
- If it says "BUY" - it tried to buy the stock
- If it says "SELL" - it tried to sell the stock
- If it says "HOLD" - it decided to wait

Check your Alpaca account to see if any orders were placed.

## Test Without Real Trading

Double-click `test.bat` to see how the bot would work with fake data. It shows sample trades and if it made or lost money.

## Important Safety Rules

- **Always use paper trading first!** This uses fake money so you can't lose real money while learning.
- **Start small** - only trade with small amounts you can afford to lose.
- **Watch what happens** - check your Alpaca account after each trade.
- **Learn slowly** - don't rush to use real money.

## If Something Goes Wrong

### Bot Won't Start:
- Make sure `.env` file exists and has your codes
- Try running as administrator (right-click start.bat → Run as administrator)

### No Signals Received:
- Check the webhook URL is exactly: `http://localhost:8000/webhook`
- Make sure the "secret" in TradingView matches "my_secret_token"

### Orders Not Working:
- Check your Alpaca API keys are correct
- Make sure you're using paper trading URL

### News Not Working:
- Check your NewsAPI key is correct
- The bot can still work without news, it just won't be as smart

## Questions?

If you get stuck, ask for help! The bot is designed to be simple, but computers can be tricky sometimes.

Remember: This is for learning. Trading with real money can lose you money. Always be careful and learn first with fake money!
