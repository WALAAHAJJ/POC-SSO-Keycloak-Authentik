import http from 'k6/http';
import crypto from 'k6/crypto';
import { check, fail } from 'k6';
import { Trend } from 'k6/metrics';

const BASE = 'http://host.docker.internal:9000';
const CLIENT = 'catalogue-client';
const REDIRECT = 'https://oauth.pstmn.io/v1/callback';
const AUTH = BASE + '/application/o/authorize/';
const TOKEN = BASE + '/application/o/token/';
const FLOW = BASE + '/api/v3/flows/executor/default-authentication-flow/';

const username = __ENV.AK_USERNAME;
const password = __ENV.AK_PASSWORD;

const dureeAuth = new Trend('duree_authentification_ms', true);

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

const headers = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

function absolue(location, origine = BASE) {
  if (location.startsWith('http://localhost:9000')) {
    return location.replace('http://localhost:9000', BASE);
  }
  if (location.startsWith('http://127.0.0.1:9000')) {
    return location.replace('http://127.0.0.1:9000', BASE);
  }
  if (location.startsWith('/')) {
    return BASE + location;
  }
  if (location.startsWith('?')) {
    return origine.split('?')[0] + location;
  }
  return location;
}

function chemin(url) {
  return url.split('?')[0]
    .replace(/^https?:\/\/[^/]+/, '');
}

function executer(method, url, data = null) {
  let adresse = url;

  for (let i = 0; i < 10; i++) {
    const options = {
      redirects: 0,
      headers,
      tags: { phase: 'authentik_flow' },
    };

    const res = method === 'GET'
      ? http.get(adresse, options)
      : http.post(adresse, JSON.stringify(data), options);

    if ([301, 302, 303, 307, 308].includes(res.status)) {
      const location = res.headers.Location;

      if (!location) fail('Redirection sans Location');

      adresse = absolue(location, adresse);
      method = 'GET';
      continue;
    }

    if (res.status !== 200) {
      fail('Flux Authentik HTTP ' + res.status);
    }

    let resultat;
    try {
      resultat = res.json();
    } catch (e) {
      fail('Réponse du flux non JSON');
    }

    if (resultat.response_errors) {
      fail('Erreur de validation du flux Authentik');
    }

    return resultat;
  }

  fail('Trop de redirections Authentik');
}

export default function () {
  if (!username || !password) {
    fail('Identifiants de test manquants');
  }

  http.cookieJar().clear(BASE);

  // 1. Initialiser OAuth2 PKCE
  const verifier = crypto.sha256(
    `${__VU}:${__ITER}:${Date.now()}:${Math.random()}`,
    'hex'
  );

  const challenge = crypto.sha256(verifier, 'base64rawurl');
  const state = crypto.sha256(
    `${Date.now()}:${Math.random()}`,
    'hex'
  );

  const authUrl =
    `${AUTH}?client_id=${CLIENT}` +
    '&response_type=code' +
    '&scope=openid%20profile%20email%20roles' +
    `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
    `&code_challenge=${challenge}` +
    '&code_challenge_method=S256' +
    `&state=${state}`;

  const debut = Date.now();

  const initial = http.get(authUrl, {
    redirects: 0,
    tags: { phase: 'autorisation_oauth2' },
  });

  if (__ENV.DEBUG === '1') console.log('Autorisation initiale : HTTP ' + initial.status);

  if (![301, 302, 303, 307, 308].includes(initial.status)) {
    fail('Autorisation OAuth2 non redirigée');
  }

  const locationInitiale = initial.headers.Location || '';

  if (__ENV.DEBUG === '1') console.log('Flux initial : ' + chemin(locationInitiale));

  // Conserver le query string du flux OAuth2
  const indexQuery = locationInitiale.indexOf('?');
  const queryFlux = indexQuery >= 0
    ? locationInitiale.substring(indexQuery + 1)
    : '';

  const adresseFlux = FLOW + '?query=' +
    encodeURIComponent(queryFlux);

  // 2. Authentification Authentik
  let data = executer('GET', adresseFlux);
  let destination = '';

  for (let i = 0; i < 10; i++) {
    const component = data.component;

    if (__ENV.DEBUG === '1') console.log(`Étape ${i + 1} : ${component}`);

    if (component === 'ak-stage-identification') {
      data = executer('POST', adresseFlux, {
        component,
        uid_field: username,
        ...(data.password_fields ? { password } : {}),
      });
    } else if (component === 'ak-stage-password') {
      data = executer('POST', adresseFlux, {
        component,
        password,
      });
    } else if (component === 'ak-stage-user-login') {
      data = executer('POST', adresseFlux, {
        component,
        remember_me: false,
      });
    } else if (component === 'xak-flow-redirect') {
      destination = data.to || '';
      if (__ENV.DEBUG === '1') console.log('Destination : ' + chemin(destination));
      break;
    } else {
      fail('Étape non prise en charge : ' + component);
    }
  }

  if (!destination) {
    fail('Fin du parcours Authentik non atteinte');
  }

  // 3. Poursuivre les redirections OAuth2
  let adresse = absolue(destination);

  // Si le flux renvoie seulement /, reprendre
  // l'autorisation avec la session authentifiée.
  if (chemin(adresse) === '/') {
    adresse = authUrl;
  }

  let code = '';
  let etatRetour = '';

  for (let i = 0; i < 15; i++) {
    const res = http.get(adresse, {
      redirects: 0,
      tags: { phase: 'callback_oauth2' },
    });

    const location = res.headers.Location || '';

    if (__ENV.DEBUG === '1') console.log(
      `Redirection OAuth2 ${i + 1} : HTTP ${res.status} ` +
      chemin(location || adresse)
    );

    if (location.includes('code=') &&
        location.includes('state=')) {
      const params = location.split('?')[1] || '';

      const elements = {};
      params.split('&').forEach(partie => {
        const index = partie.indexOf('=');
        if (index >= 0) {
          elements[partie.substring(0, index)] =
            decodeURIComponent(partie.substring(index + 1));
        }
      });

      code = elements.code || '';
      etatRetour = elements.state || '';
      break;
    }

    if ([301, 302, 303, 307, 308].includes(res.status) &&
        location) {
      adresse = absolue(location, adresse);

      if (adresse.startsWith(REDIRECT)) {
        fail('Callback sans code OAuth2');
      }
      continue;
    }

    fail(
      'Parcours OAuth2 interrompu : HTTP ' + res.status +
      ' sur ' + chemin(adresse)
    );
  }

  const codeValide = Boolean(code && etatRetour === state);

  check(null, {
    'Code OAuth2 valide': () => codeValide,
  });

  if (!codeValide) {
    fail('Code OAuth2 absent ou state incorrect');
  }

  // 4. Échanger le code contre un token
  const token = http.post(
    TOKEN,
    {
      grant_type: 'authorization_code',
      client_id: CLIENT,
      code,
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
    'Access Token reçu': () => succes,
  });

  if (!succes) {
    fail('Échange token échoué : HTTP ' + token.status);
  }

  const duree = Date.now() - debut;
  dureeAuth.add(duree);

  if (__ENV.DEBUG === '1') console.log('Authentification OAuth2 réussie : ' + duree + ' ms');
  if (__ENV.DEBUG === '1') console.log('JWT reçu : OUI');
}
