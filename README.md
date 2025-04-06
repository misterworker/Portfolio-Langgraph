# Portfolio-Langgraph

Langgraph Bot created to serve users of Ethan's portfolio.
Portfolio Website: https://portfolio-phi-mocha-72.vercel.app/
Github link to portfolio website: https://github.com/misterworker/Portfolio

To test:
1. pip install -r requirements.txt
2. Add env file to root and scripts/github
3. Fill root env file with OPENAI_API_KEY, PINECONE_API_KEY, DB_URI, GITHUB_CONTRIBUTIONS
4. Fill scripts/github env file with GIT_TOKEN and AGENT_LINK
5. uvicorn main:app --reload --port 8000
6. python __tests__/apiTest.py
7. cd scripts/github
8. uvicorn contributions_by_year:app --reload --port 8001
