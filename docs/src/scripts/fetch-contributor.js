// scripts/fetch-contributors.js (version avec module natif https)
const https = require('https');
const fs = require('fs');
const path = require('path');
const GITHUB_TOKEN = process.env.GITHUB_TOKEN; // Token optionnel pour augmenter le rate-limit

function fetchUrl(url) {
  return new Promise((resolve, reject) => {
    const headers = {
      'User-Agent': 'Node.js'
    };
    if (GITHUB_TOKEN) {
      headers['Authorization'] = `token ${GITHUB_TOKEN}`;
    }
    
    https.get(url, { headers }, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode}: ${res.statusMessage}`));
        } else {
          resolve(JSON.parse(data));
        }
      });
    }).on('error', (err) => {
      reject(err);
    });
  });
}

async function fetchContributors(owner, repo) {
  let contributors = [];
  let page = 1;
  
  while (true) {
    const url = `https://api.github.com/repos/${owner}/${repo}/contributors?per_page=100&page=${page}`;
    console.log(`Fetching page ${page}...`);
    const data = await fetchUrl(url);
    
    if (data.length === 0) break;
    contributors = contributors.concat(data);
    page++;
  }
  
  return contributors;
}

async function main() {
  try {
    const owner = 'etalab-ia';
    const repo = 'OpenGateLLM';
    console.log(`Fetching contributors for ${owner}/${repo}...`);
    const list = await fetchContributors(owner, repo);
    
    // Extraire seulement les champs utiles
    const simplified = list.map(user => ({
      login: user.login,
      avatar_url: user.avatar_url,
      html_url: user.html_url,
      contributions: user.contributions,
    }));
    
    // Créer le dossier si nécessaire
    const dataDir = path.join(__dirname, '..', 'data');
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    
    const outPath = path.join(dataDir, 'contributors.json');
    fs.writeFileSync(outPath, JSON.stringify(simplified, null, 2));
    console.log(`✅ ${simplified.length} contributeurs enregistrés dans ${outPath}`);
  } catch (e) {
    console.error('❌ Error fetching contributors:', e.message);
    process.exit(1);
  }
}

main();
