# RUMI Outreach — Instructions for Claude Code

## Goal
Post about RUMI on Dev.to and Reddit using Composio MCP tools.

## Step 1: Post on Dev.to

Use the Composio MCP tool `devto_create_article` (or similar) with these params:
- **title**: "I Built an AI That Does Autonomous Scientific Discovery — Here's What It Found"
- **body_markdown**: contents of `devto_post.md` in this folder
- **published**: true
- **tags**: ai, research, openscience, python
- **canonical_url**: https://github.com/subhansh-dev/Rumi

If the tool needs different param names, adapt accordingly. The Dev.to connected account on Composio is ACTIVE.

## Step 2: Post on Reddit

Use the Composio MCP tool for Reddit (reddit_create_post or similar) with:
- **title**: "I built an open-source AI that autonomously reads scientific papers, builds knowledge graphs, and generates novel hypotheses — here's what it found when analyzing cancer drug resistance"
- **body**: contents of `reddit_post.md` in this folder
- **subreddit**: Try these in order — r/MachineLearning, r/artificial, r/opensource, r/bioinformatics, r/LocalLLaMA

If r/MachineLearning has strict rules, try r/artificial or r/opensource first.

## Step 3: Verify

After posting, report back:
- Dev.to article URL
- Reddit post URL
- Any errors encountered

## Context
- GitHub: https://github.com/subhansh-dev/Rumi
- Portfolio: https://subhanshh.vercel.app
- RUMI is still in early stages, actively being developed
- Best discovery: KRAS G12C cancer drug resistance analysis (14 PubMed papers, knowledge graph, hypothesis generation)

## Files in this folder
- `devto_post.md` — Full Dev.to article
- `reddit_post.md` — Full Reddit post
- `INSTRUCTIONS.md` — This file
