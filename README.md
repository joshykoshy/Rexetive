# Rexetive

> AI-verified knowledge sharing platform with tamper-proof Sui NFT minting.

🏆 **Finalist Project** at the **SuiHub Decentralized Autonomy Blockathon** (Sui Foundation, May 2025)

---

## Overview

**Rexetive** is a decentralized knowledge-sharing and investigative analysis platform designed to combat misinformation and reward high-quality insights. By combining OpenAI large language models with Sui Move smart contracts, Rexetive creates a tamper-proof pipeline where user theories, case breakdowns, and analytical hypotheses are independently evaluated for logic, plausibility, and bias. Submissions that meet strict quality thresholds are minted directly onto the Sui blockchain as non-fungible tokens (NFTs), creating a permanent, verifiable registry of community-contributed knowledge.

---

## Key Features

- **Multi-Perspective AI Evaluation**: Four specialized analysis modes powered by OpenAI GPT-4:
  - **Synopsis Evaluation**: Quantitative scoring across Clarity, Plausibility, Consistency, and Relevance (0–10 each), plus safety checks and quality rankings (Gold, Silver, Bronze).
  - **Logic & Timeline Analysis**: Automatic detection of chronological contradictions, logical fallacies, and narrative gaps.
  - **Hypothesis Verification**: Plausibility assessment with generated counterpoints, evidence matching, and suggested investigation angles.
  - **Bias & Fallacy Detection**: Identifies confirmation bias, emotional bias, and logical leaps with an objectivity rating.
- **Quality-Gated NFT Minting**: Insights achieving a score of &ge; 30/40 and passing safety filters are automatically minted as immutable `ValidSubmission` NFTs transferred to the contributor's Sui wallet.
- **On-Chain Reputation System**: Dynamic `UserReputation` objects deployed on Sui track accepted submissions, cumulative points, and total minted NFTs.
- **Wallet-Native Authentication**: Passwordless authentication via Sui browser wallets using `@mysten/dapp-kit` with custom header-based session verification.
- **Interactive Case Explorer**: Built-in repository of investigative case studies with real-time community submission feeds and detailed breakdowns.

---

## Architecture

Rexetive connects a React-based frontend, a high-performance FastAPI orchestration layer, OpenAI's reasoning models, and the Sui Move blockchain:

```
┌─────────────────────────────────────────────────────────┐
│                   React 19 + Vite UI                    │
│      (@mysten/dapp-kit Wallet Connect & Case Tools)     │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP / JSON (Axios)
                             ▼
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Backend                     │
│  - Session & Wallet Auth (SQLite3 users.db)             │
│  - AI Evaluation Pipeline Orchestration                 │
│  - Sui Client Transaction Dispatcher (pysui)            │
└──────────────┬───────────────────────────┬──────────────┘
               │                           │
               ▼                           ▼
┌─────────────────────────────┐ ┌─────────────────────────┐
│       OpenAI GPT-4 API      │ │    Sui Move Package     │
│  - Multi-dimensional scoring│ │  - Submissions Store    │
│  - Logic & Bias analysis    │ │  - ValidSubmission NFT  │
│  - Safety & rank tagging    │ │  - UserReputation Object│
└─────────────────────────────┘ └─────────────────────────┘
```

### Component Breakdown

1. **Frontend (`frontend/`)**:
   - Single-Page Application (SPA) built with React 19, Vite, and Radix UI Themes.
   - Integrates `@mysten/dapp-kit` for non-custodial Sui wallet connection (Devnet).
   - Dedicated pages for Case Analysis, Synopsis Evaluation, Timeline Logic, Hypothesis Verification, and User Submissions.
2. **Backend (`backend/`)**:
   - Asynchronous REST API powered by FastAPI and Uvicorn.
   - Interfaces with OpenAI via the official SDK using structured JSON schema prompts.
   - Manages on-chain transactions and calls Move entry functions via `pysui`.
3. **Smart Contracts (`move/rex/`)**:
   - Written in Sui Move (`edition = "2024.beta"`).
   - `Submissions`: Shared object holding a table of all community submissions with emitted events.
   - `ValidSubmission`: Ownable NFT minted and transferred to authors of validated submissions.
   - `UserReputation`: On-chain user profile recording reputation points, accepted submissions, and NFT counts.
4. **Data Layer**:
   - `users.db`: Lightweight SQLite database for local wallet authentication state and user registry.

---

## Tech Stack

| Layer | Technologies / Frameworks |
|---|---|
| **Smart Contracts** | Sui Move, Sui Framework (`devnet`) |
| **Backend** | Python 3.12, FastAPI, Uvicorn, Pydantic, `pysui`, OpenAI Python SDK, `python-jose`, `python-dotenv`, SQLite3 |
| **Frontend** | React 19, Vite, JavaScript (ES modules), `@mysten/dapp-kit`, `@mysten/sui`, Radix UI Themes, Radix UI Icons, TanStack React Query, React Router DOM 7, Axios, CSS Modules |
| **Tools & Environment** | Sui CLI, Node.js, npm, Git |

---

## Project Structure

```
Rexetive/
├── backend/
│   ├── ai_utils.py             # OpenAI prompt evaluation routines
│   ├── blockchain_utils.py     # pysui SDK client & Move contract calls
│   ├── main.py                 # FastAPI endpoints & route handlers
│   ├── requirements.txt        # Python backend dependencies
│   ├── user_auth.py            # SQLite user registry & wallet auth
│   └── .gitignore
├── frontend/
│   ├── public/                 # Static assets & case study fixtures
│   ├── src/
│   │   ├── components/         # Navbar, ProtectedRoute, Case Tools
│   │   ├── contexts/           # AuthContext for Sui wallet state
│   │   ├── pages/              # Case synopsis, logic, bias, and submissions pages
│   │   ├── utils/              # Axios API client setup
│   │   ├── App.jsx             # Main router & wallet auth wrapper
│   │   └── main.jsx            # React root with Sui dApp Kit provider
│   ├── package.json            # Node.js dependencies & scripts
│   ├── vite.config.js          # Vite bundler configuration
│   └── .gitignore
├── move/
│   └── rex/
│       ├── sources/
│       │   └── rex.move        # Sui Move contracts (NFT, Submissions, Reputation)
│       ├── tests/
│       │   └── fintech_tests.move # Unit tests for Move contracts
│       ├── Move.toml           # Sui package manifest
│       └── Move.lock
├── .gitignore                  # Root gitignore (.venv, node_modules, build artifacts)
├── LICENSE                     # MIT License
├── README.md                   # Project documentation
└── Rexetive.desc               # Original project abstract
```

---

## Setup & Installation

### Prerequisites

- **Python**: Version 3.10 or higher
- **Node.js**: Version 18 or higher (with npm)
- **Sui CLI**: Installed and configured with an active Sui Devnet address
- **OpenAI API Key**: With access to GPT-4 models

---

### 1. Smart Contract Setup (Sui Move)

```bash
cd move/rex

# Run unit tests
sui move test

# Build the Move package
sui move build

# Publish to Sui Devnet (optional, if deploying your own instance)
sui client publish --gas-budget 100000000
```

> Take note of the published `Package ID` and shared `Submissions` Object ID to populate your backend configuration.

---

### 2. Backend Setup (FastAPI)

```bash
cd backend

# Create and activate a Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
SUI_RPC_URL=https://fullnode.devnet.sui.io:443
SUI_PRIVATE_KEY=your_sui_private_key_here
SUI_ADDRESS=your_sui_wallet_address_here
PREDICTIONS_PACKAGE_ID=your_deployed_package_id
SUBMISSIONS_OBJECT_ID=your_shared_submissions_object_id
PREDICTIONS_MODULE_NAME=rex
GAS_BUDGET=20000000
JWT_SECRET_KEY=your_jwt_secret_key_here
```

Start the backend server:

```bash
uvicorn main:app --reload --port 8000
```

The API documentation will be available at `http://localhost:8000/docs`.

---

### 3. Frontend Setup (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Open `http://localhost:5173` in your browser and connect your Sui Devnet wallet (e.g., Sui Wallet, Nightly, or Ethos).

---

## Award & Recognition

- **Finalist** — **SuiHub Decentralized Autonomy Blockathon** (Organized by the Sui Foundation, May 2025).
- Recognized for building an autonomous, AI-gated on-chain knowledge validation and reputation pipeline on the Sui network.

---

## Future Work

- **Community Staking & Peer Verification**: Allow other researchers to stake SUI tokens to challenge or endorse AI-validated findings through a decentralized review DAO.
- **Multi-Agent Cross Examination**: Introduce competing AI evaluators to debate edge-case theories before submitting verdicts on-chain.
- **Sui Mainnet Deployment**: Transition contract package and reputation primitives to Sui Mainnet with enhanced dynamic NFT visual traits.
- **Zero-Knowledge Whistleblower Mode**: Implement zk-SNARK / zk-Login primitives to enable anonymous submissions while preserving cryptographic proof of insight validity.

---

## License

This project is licensed under the [MIT License](LICENSE).
