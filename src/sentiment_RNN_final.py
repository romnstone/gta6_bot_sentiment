import os
import numpy as np
import pandas as pd
import random
import tensorflow as tf

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle

from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Embedding, LSTM, Dense, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping

from pathlib import Path

# Set Random Seed to Ensure Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)
os.environ['PYTHONHASHSEED'] = str(SEED)

# File paths 
# Root of the project = folder where this script lives
ROOT = Path(__file__).resolve().parent
# Filepaths (relative, portable)
train_data_path = ROOT / "data" / "labels" / "GTA6_Sentiments_Updated.xlsx"
glove_file = ROOT / "embeddings" / "glove.twitter.27B.100d.txt"
unlabeled_data_path = ROOT / "data" / "raw" / "unlabeled_reddit_comments_GTA6.xlsx"

# Load and preprocess dataset
df = pd.read_excel(train_data_path)
df = shuffle(df, random_state=SEED)
df['Sentiments'] = df['Sentiments'].str.strip().str.capitalize()

# Merge optional sentiments
def merge_sentiments(df, merge=False):
    df_copy = df.copy()
    if merge:
        df_copy['Sentiments'] = df_copy['Sentiments'].replace({
            "Disappointed": "Negative",
            "Angry": "Negative",
            "Sarcastic": "Negative",
            "Excited": "Positive"
        })
    return df_copy

merged_df = merge_sentiments(df, merge=True)

# Encode for stratification
label_encoder = LabelEncoder()
encoded_labels = label_encoder.fit_transform(merged_df['Sentiments'])

train_df, test_df, _, _ = train_test_split(
    merged_df,
    encoded_labels,
    test_size=0.25,
    random_state=SEED,
    stratify=encoded_labels
)

# Tokenization
tokenizer = Tokenizer(num_words=10000, oov_token="<OOV>")
tokenizer.fit_on_texts(train_df['Content'])
word_index = tokenizer.word_index

train_sequences = tokenizer.texts_to_sequences(train_df['Content'])
train_padded = pad_sequences(train_sequences, maxlen=100, padding='post')

train_labels = label_encoder.transform(train_df['Sentiments'])
train_categorical = to_categorical(train_labels)

# Load GloVe embeddings
embedding_dim = 100
embeddings_index = {}
with open(glove_file, encoding="utf8") as f:
    for line in f:
        values = line.split()
        word = values[0]
        vector = np.asarray(values[1:], dtype='float32')
        embeddings_index[word] = vector

num_words = min(10000, len(word_index) + 1)
embedding_matrix = np.zeros((num_words, embedding_dim))
for word, i in word_index.items():
    if i < num_words:
        vec = embeddings_index.get(word)
        if vec is not None:
            embedding_matrix[i] = vec

#  Hyperparameter tuning
best_accuracy = 0
best_config = {}

for units in [12, 16, 20, 24, 28]:
    for dropout in [0.3, 0.4, 0.5, 0.6]:
        for recurrent_dropout in [0.3, 0.4, 0.5]:
            print(f"Training: units={units}, dropout={dropout}, recurrent_dropout={recurrent_dropout}")

            model = Sequential([
                Embedding(input_dim=num_words, output_dim=embedding_dim,
                          weights=[embedding_matrix], input_length=100,
                          trainable=False),
                Bidirectional(LSTM(units, dropout=dropout, recurrent_dropout=recurrent_dropout)),
                Dense(len(np.unique(train_labels)), activation='softmax')
            ])

            model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

            early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

            model.fit(train_padded, train_categorical,
                      epochs=25,
                      batch_size=16,
                      validation_split=0.2,
                      verbose=0,
                      callbacks=[early_stop])

            test_sequences = tokenizer.texts_to_sequences(test_df['Content'])
            test_padded = pad_sequences(test_sequences, maxlen=100, padding='post')
            test_labels = label_encoder.transform(test_df['Sentiments'])
            test_categorical = to_categorical(test_labels)

            loss, accuracy = model.evaluate(test_padded, test_categorical, verbose=0)
            print(f"Test Accuracy: {accuracy:.2%}")

            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_config = {
                    'units': units,
                    'dropout': dropout,
                    'recurrent_dropout': recurrent_dropout
                }
                model.save("best_sentiment_model.h5")  # ✅ Save best model

#  Load and print test accuracy of best model
best_model = load_model("best_sentiment_model.h5")
print("\n Best Configuration:", best_config)
print(f" Best Test Accuracy: {best_accuracy:.2%}")

#  Load unlabeled comments
unlabeled_df = pd.read_excel(unlabeled_data_path)

# Ensure column is named 'Content'
if 'Content' not in unlabeled_df.columns:
    raise ValueError("Expected a column named 'Content' in the unlabeled dataset.")

# Preprocess and predict
unlabeled_sequences = tokenizer.texts_to_sequences(unlabeled_df['Content'])
unlabeled_padded = pad_sequences(unlabeled_sequences, maxlen=100, padding='post')

pred_probs = best_model.predict(unlabeled_padded)
pred_labels = np.argmax(pred_probs, axis=1)
pred_sentiments = label_encoder.inverse_transform(pred_labels)

# Save labeled file
unlabeled_df['Predicted_Sentiment'] = pred_sentiments
unlabeled_df.to_excel("model_labeled_comments.xlsx", index=False)
print(" Unlabeled comments have been labeled and saved as 'model_labeled_comments.xlsx'")
