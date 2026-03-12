# Spotify Listening Data Explorer

An interactive Streamlit application for analyzing personal Spotify listening history with statistical insights and nice visualizations.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)


## Features

### Data Analysis

- **Top Content** — Explore your most-played artists, tracks, and albums
- **Temporal Analysis** — Visualize listening patterns by hour, day, and month
- **Valid Streams Filtering** — Understand Spotify's 30-second threshold and its impact on your stats
- **Hypothesis Testing** — Statistical tests on naive listening behavior hypotheses:
  - Pareto Principle (80/20 rule)
  - Platform comparison (mobile vs desktop)
  - Time-of-day listening patterns

### Two Modes 🎭 

**Demo Mode** — Try the app instantly with pre-loaded sample data (author's listening history)

**Upload Mode** — Analyze your own Spotify Extended Streaming History


## How to use

### Option 1: Try Online (Recommended)
Visit the [HuggingFace Space](https://huggingface.co/spaces/teolepv/listening-audio-explorer)

### Option 2: Run Locally

**Prerequisites:** Python 3.13+, pip

### Installation
1. **Clone the repository**
```bash
git clone https://github.com/YOUR-USERNAME/spotify-listening-explorer.git
cd spotify-listening-explorer
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the app**
```bash
streamlit run app.py
```

5. The app will open at `http://localhost:8501`. Choose your mode (demo or upload your data) and explore the application.


## Data (If you want to get your own spotify data)
1. Go to [Spotify Account Privacy Settings](https://www.spotify.com/account/privacy/)
2. Request **Extended Streaming History**
3. Wait for email (between 1-30 days)
4. Download and extract the zip files
5. Upload the `Streaming_History_Audio_*.json` to the app

## Privacy & Security

### Demo Data
- Real listening history from the author with all sensitive information removed.
- Only music preferences and temporal patterns are visible


### Your Data
- Processed **entirely client-side** in your browser
- **Never stored** on any server
- **Complete privacy**: Your data stays with you


## Project Structure

```
repository/
├── app.py                 # Main Streamlit application
├── demo_data/             # Pre-processed demo data 
│   ├── streams_all.parquet
│   └── streams_valid.parquet
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore patterns
└── README.md              # This file
```


## Author
**Teo Le Provost**  
Data Science & Business Analytics Master Student 
University of Warsaw  

Originally developed as a final project for Introduction to Python and SQL course (January 2026), and extended with additional features for portfolio purposes.


## 📧 Contact

Feel free to reach out for questions or collaboration!

- [GitHub](https://github.com/lepvteo)
- [LinkedIn](https://www.linkedin.com/in/téo-le-provost-689a611b3/en)


## License
MIT License
This app is not affiliated with Spotify. It's an independent project initially submitted as academic coursework for educational purposes.