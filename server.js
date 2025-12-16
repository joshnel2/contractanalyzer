const express = require('express');
const { AzureOpenAI } = require('openai');
const path = require('path');

const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(express.static('public'));

const client = new AzureOpenAI({
  endpoint: process.env.AZURE_OPENAI_ENDPOINT,
  apiKey: process.env.AZURE_OPENAI_API_KEY,
  apiVersion: '2024-02-15-preview'
});

app.post('/calculate', async (req, res) => {
  try {
    const { caseData, rulesSheet } = req.body;

    const response = await client.chat.completions.create({
      model: process.env.AZURE_OPENAI_DEPLOYMENT,
      temperature: 0,
      messages: [
        {
          role: 'system',
          content: `You are a CSV calculator. Return ONLY raw CSV data. No markdown. No explanation. No code blocks.`
        },
        {
          role: 'user',
          content: `Calculate attorney commissions.

CASE DATA:
${caseData}

RULES SHEET:
${rulesSheet}

RULES:
1. User Pay = total collected × user percentage (match attorney name to user)
2. If user = originator (same person): leave originator percentage and originator pay EMPTY
3. If user ≠ originator: Originator Pay = User Pay × originator's "own origination other work percentage"

Return CSV with headers:
matter,date,user,originator,total collected,user percentage,user pay,originator percentage,originator pay

Output the CSV now, starting with the header row:`
        }
      ]
    });

    let csv = response.choices[0].message.content;
    csv = csv.replace(/```csv\n?/g, '').replace(/```\n?/g, '').trim();

    res.json({ csv });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
});

const port = process.env.PORT || 8080;
app.listen(port, () => console.log(`Server running on port ${port}`));
