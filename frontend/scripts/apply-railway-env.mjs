import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const envProdPath = path.resolve(__dirname, '..', 'src', 'environments', 'environment.prod.ts');

function normalizeApiUrl(value) {
  let apiUrl = String(value).trim();
  apiUrl = apiUrl.replace(/\/+$/, '');
  if (!apiUrl.endsWith('/api')) {
    apiUrl = `${apiUrl}/api`;
  }
  return apiUrl;
}

function applyApiUrlToEnvironmentProdTs(fileContent, apiUrl) {
  const next = fileContent.replace(
    /apiUrl\s*:\s*'[^']*'/,
    `apiUrl: '${apiUrl.replace(/'/g, "\\'")}'`
  );

  if (next === fileContent) {
    throw new Error(
      "No se pudo actualizar environment.prod.ts (no encontré el campo apiUrl: '...')."
    );
  }

  return next;
}

try {
  const apiUrlRaw = process.env.API_URL;
  if (!apiUrlRaw) {
    console.log(
      '[apply-railway-env] API_URL no está definida. Mantengo environment.prod.ts sin cambios.'
    );
    process.exit(0);
  }

  const apiUrl = normalizeApiUrl(apiUrlRaw);
  const current = fs.readFileSync(envProdPath, 'utf8');
  const updated = applyApiUrlToEnvironmentProdTs(current, apiUrl);

  if (updated !== current) {
    fs.writeFileSync(envProdPath, updated, 'utf8');
    console.log(`[apply-railway-env] environment.prod.ts actualizado: apiUrl=${apiUrl}`);
  } else {
    console.log('[apply-railway-env] Sin cambios (apiUrl ya estaba igual).');
  }
} catch (err) {
  console.error('[apply-railway-env] ERROR:', err?.message ?? err);
  process.exit(1);
}
