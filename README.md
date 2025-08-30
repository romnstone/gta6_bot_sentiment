# Bot Detection + Sentiment Analysis on Reddit (GTA6)

This project builds an end-to-end pipeline to (1) scrape Reddit threads about GTA6, (2) detect bot-like comments using **unsupervised anomaly detection**, and (3) classify sentiments with a **Bidirectional LSTM**.

## Highlights
- **Scraping**: Pulls user/timestamp/content from multiple GTA6 threads and appends to Excel for downstream analysis. (See `src/webscraping_content.py`.)  
- **Bot detection**: Uses Isolation Forest, One-Class SVM, and DBSCAN with majority vote at both user and comment levels.
- **My role (exclusive):** I designed, implemented, and evaluated this bot detection module.
- **Sentiment model**: Tokenization + pre-trained **GloVe** embeddings + BiLSTM, hyperparameter sweep over 60 configs; saves the **best** model and labels unlabeled comments. (See `src/sentiment_RNN_final.py`.)

## Repo Structure
- `src/` – scraping + modeling code  
- `notebooks/` – exploratory notebooks  
- `data/` – (ignored by default) raw/processed datasets  
- `reports/` – final PDF report

## Setup
```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
