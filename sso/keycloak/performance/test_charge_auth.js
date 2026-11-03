
import http from 'k6/http';
import crypto from 'k6/crypto';
import { check } from 'k6';
import { parseHTML } from 'k6/html';
import { Trend } from 'k6/metrics';

const BASE = 'http://host.docker.internal:8080';
const REALM = 'collector-poc';
const CLIENT = 'catalogue-client';
const REDIRECT = 'http://127.0.0.1:8765/callback';

const dureeAuthentification = new Trend(
  'duree_authentification_ms',
  true
);

// Identifiants stockés uniquement sur le Mac
const comptes = open('/secrets/loadtest-credentials.csv')
  .trim()
  .split(/\r?\n/)
  .slice(1)
  .map(ligne => {
    const [username, password] = ligne.split(',');
    return { username, password };
  });

export const options = {
  scenarios: {
    authentifications: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '15s', target: 5 },
        { duration: '15s', target: 10 },
        { duration: '15s', target: 20 },
        { duration: '15s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    checks: ['rate>0.95'],
    http_req_failed: ['rate<0.05'],
  },
};

// Adapter les URL Keycloak pour Docker
function urlDocker(url, origine = BASE) {
  const propre = url.replace(/&amp;/g, '&');

  if (
    propre.startsWith('http://localhost:8080') ||
    propre.startsWith('http://127.0.0.1:8080')
  ) {
    return propre.replace(
      /^http:\/\/(localhost|127\.0\.0\.1):8080/,
      BASE
    );
  }

  if (propre.startsWith('/')) {
    return BASE + propre;
  }

  if (propre.startsWith('?')) {
    return origine.split('?')[0] + propre;
  }

  return propre;
}

// Suivre les redirections vers Keycloak
function obtenirPageConnexion(url) {
  let adresse = url;

  for (let i = 0; i < 10; i++) {
    const reponse = http.get(adresse, {
      redirects: 0,
      tags: { phase: 'page_connexion' },
    });

    if (reponse.status === 200) {
      return reponse;
    }

    if ([301, 302, 303, 307, 308].includes(reponse.status)) {
      const location = reponse.headers.Location;

      if (!location) {
        throw new Error('Redirection sans Location');
      }

      adresse = urlDocker(location, adresse);
      continue;
    }

    throw new Error(
      `Erreur page connexion : HTTP ${reponse.status}`
    );
  }

  throw new Error('Trop de redirections Keycloak');
}

export default function () {
  const compte = comptes[(__VU - 1) % comptes.length];

  // Nouvelle session pour chaque connexion
  http.cookieJar().clear(BASE);

  const verifier =
    crypto.sha256(
      `${compte.username}-${Date.now()}-${Math.random()}`,
      'hex'
    ) +
    crypto.sha256(`${Math.random()}`, 'hex');

  const challenge = crypto.sha256(verifier, 'base64rawurl');
  const state = crypto.sha256(`${Math.random()}`, 'hex');

  const authUrl =
    `${BASE}/realms/${REALM}/protocol/openid-connect/auth?` +
    `client_id=${CLIENT}` +
    '&response_type=code' +
    '&scope=openid' +
    `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
    `&code_challenge=${challenge}` +
    '&code_challenge_method=S256' +
    `&state=${state}`;

  // 1. Obtenir le formulaire de connexion
  const page = obtenirPageConnexion(authUrl);

  const formulaire = parseHTML(page.body).find('#kc-form-login');
  const action = formulaire.attr('action');

  if (!action) {
    throw new Error(
      `Formulaire Keycloak introuvable : HTTP ${page.status}`
    );
  }

  // 2. Soumettre les identifiants
  const debut = Date.now();

  const connexion = http.post(
    urlDocker(action),
    {
      username: compte.username,
      password: compte.password,
      credentialId: '',
    },
    {
      redirects: 0,
      tags: { phase: 'soumission_identifiants' },
    }
  );

  // 3. Diagnostic sans afficher les informations sensibles
  const location = connexion.headers.Location || '';

  console.log(`Statut connexion : ${connexion.status}`);

  if (location) {
  // Afficher uniquement le chemin, jamais les paramètres OAuth2
  const chemin = location
    .split('?')[0]
    .split('#')[0]
    .replace(/^https?:\/\/[^/]+/, '');

  console.log(`Redirection vers : ${chemin}`);
} else {
  console.log('Aucune redirection OAuth2');
}
  // Vérifier si Keycloak a renvoyé un formulaire d'erreur
  if (connexion.status === 200) {
    const pageErreur = parseHTML(connexion.body);

    if (pageErreur.find('#kc-form-login').size() > 0) {
      console.error(
        'Keycloak affiche encore le formulaire de connexion.'
      );
      console.error(
        'Vérifier les identifiants et les éventuelles erreurs.'
      );
    }
  }

  // 4. Extraire le code OAuth2
  const retour = location.replace(/&amp;/g, '&');

  const code = /[?&]code=([^&]+)/.exec(retour)?.[1];
  const etatRetour = /[?&]state=([^&]+)/.exec(retour)?.[1];

  if (!code || decodeURIComponent(etatRetour || '') !== state) {
    check(connexion, {
      'Code OAuth2 valide': () => false,
    });

    console.error(
      `Connexion ${compte.username} échouée : HTTP ${connexion.status}`
    );
    return;
  }

  check(connexion, {
    'Code OAuth2 valide': () => true,
  });

  // 5. Echanger le code contre un JWT
  const token = http.post(
    `${BASE}/realms/${REALM}/protocol/openid-connect/token`,
    {
      grant_type: 'authorization_code',
      client_id: CLIENT,
      code: decodeURIComponent(code),
      redirect_uri: REDIRECT,
      code_verifier: verifier,
    },
    {
      tags: { phase: 'echange_token' },
    }
  );

  let succes = false;

  if (token.status === 200) {
    try {
      succes = Boolean(token.json('access_token'));
    } catch (e) {
      succes = false;
    }
  }

  check(token, {
    'JWT reçu': () => succes,
  });

  if (succes) {
    const duree = Date.now() - debut;
    dureeAuthentification.add(duree);

    console.log(
      `Connexion ${compte.username} réussie : ${duree} ms`
    );
  } else {
    console.error(
      `Echange JWT échoué : HTTP ${token.status}`
    );
  }
}
