# CS2 Market Intelligence Platform

## Overview

The CS2 Market Intelligence Platform is a full-stack web application that tracks, analyzes, and visualizes the in-game economy of Counter-Strike 2 skins, cases, and stickers. It combines historical price data, event-driven analysis, and trend-based indicators to help users understand market behavior and identify opportunities.

The system is designed as a portfolio-grade data analytics project focused on time-series data engineering, market insights, and lightweight predictive modeling.

---

## Goals

* Provide full price history charts starting from an item’s release date (when data is available)
* Build a continuously growing historical market database
* Identify and display market-moving events
* Generate explainable trend signals (bullish / neutral / bearish)
* Offer lightweight predictive ranges based on historical behavior
* Demonstrate full-stack, data pipeline, and analytics engineering skills

---

## Core Features

### 1. Price Tracking & Full History Charts

* Historical price charts for skins, cases, and stickers
* Data displayed from item release date (when available)
* If full historical data is unavailable, charts begin from earliest recorded snapshot
* 7-day, 30-day, 90-day, and full-lifecycle views
* Price + volume visualization over time
* Percentage change since launch and since tracked start date

---

### 2. Event Tracking System

The platform overlays key economic events that influence market behavior:

* Major tournaments and sticker capsule releases
* Case additions and removals from active drop pools
* Operation start and end cycles
* Game updates affecting supply or demand

Each event is linked to time-series data to analyze cause-and-effect relationships in price movement.

---

### 3. Trend Scoring Engine

A rule-based analytics system that evaluates market conditions using:

* Short-term vs long-term price momentum
* Volume change detection
* Volatility measurement
* Distance from major events

Outputs:

* Bullish / Neutral / Bearish classification
* Confidence score (low / medium / high)
* Explanation of contributing factors

---

### 4. Lightweight Prediction Layer

Instead of complex deep learning models, the system uses:

* Moving averages (short and long term)
* Linear regression trend projection
* Volatility-adjusted forecast ranges

Output format:

* Expected short-term movement range (e.g., +2% to +10%)
* Directional trend estimate

---

### 5. Opportunity Detection

The system identifies potentially interesting market conditions:

* Undervalued items (below historical trend baseline)
* Overheated items (rapid unsustainable growth)
* Momentum-driven items (strong directional movement)

Each item receives an opportunity score based on computed indicators.

---

### 6. Portfolio Tracker (Optional Extension)

* User inventory tracking
* Portfolio value over time
* Profit and loss calculations
* Exposure breakdown across item types

---

## Data Sources

The platform uses a hybrid data collection strategy:

### Primary Sources

* Steam Community Market data collection
* Continuous daily scraping or API-based ingestion
* Item metadata and listing snapshots

### Secondary Sources

* Community-maintained historical datasets
* Third-party market data providers

### Internal Computed Data

* Moving averages
* Volatility indicators
* Trend features
* Event correlation metrics

---

## Data Storage Model

### items

* item_id
* name
* type (skin / case / sticker)
* release_date (used to anchor full lifecycle charts)

### price_history

* id
* item_id
* timestamp
* price
* volume
* median_price (optional)

This table enables full time-series reconstruction of each item’s market history.

### events

* id
* type (major / update / case_drop / operation)
* timestamp
* description

---

## System Architecture

### Frontend

* Next.js (React-based interface)
* Interactive charts for time-series visualization
* Item detail pages with event overlays

### Backend

* Python (FastAPI) or Node.js
* REST API for market data and analytics
* Feature computation services

### Database

* Supabase (PostgreSQL)
* Stores:

  * Item metadata
  * Full price history
  * Events
  * Computed indicators

### Data Pipeline

* Scheduled daily ingestion job
* Market data collection
* Feature engineering pipeline
* Database updates and aggregation

---

## Market Context

The Counter-Strike 2 economy is a semi-structured market influenced by:

* Supply changes (case rotations and drop pool adjustments)
* Demand spikes from tournaments and events
* Speculative trading behavior
* Game updates impacting item availability

This creates cyclical patterns with both predictable trends and sudden volatility.

---

## Trend Logic (Simplified)

The system evaluates:

* Short-term vs long-term price divergence
* Volume spikes relative to baseline
* Event proximity weighting
* Historical similarity patterns

The result is a directional signal rather than an exact price prediction.

---

## MVP Scope

The initial version includes:

* Full price history charting from release or earliest available data
* Event overlay system
* Trend scoring engine
* Basic predictive range estimation

Excluded from MVP:

* Deep learning models (LSTM / neural networks)
* Real-time trading automation
* High-frequency prediction systems

---

## Future Enhancements

* Advanced machine learning forecasting (XGBoost, ARIMA)
* Market anomaly detection system
* Sentiment analysis from community discussions
* Automated alerts for opportunity detection
* Enhanced portfolio analytics and benchmarking

---

## Why This Project Is Valuable

This platform demonstrates:

* Full-stack development capabilities
* Data pipeline design and automation
* Time-series analysis and feature engineering
* Real-world application of market analytics
* Ability to build explainable analytics systems

---

## Summary

This project is a CS2 market intelligence platform that transforms raw market data into structured historical insights and actionable signals. It emphasizes full lifecycle price tracking, event correlation, and explainable trend analysis over complex black-box prediction systems.
