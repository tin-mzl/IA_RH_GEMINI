// ============================================================
// VARIABLES GLOBALES
// ============================================================
let currentUserId = null;
let currentPdfId = null;
let currentOffreId = null;
let currentEntretienId = null;

// Audio & WebSocket
let liveWs = null;
let audioContext = null;
let micStream = null;
let scriptNode = null;
let nextPlayTime = 0;

// ============================================================
// INITIALISATION
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    verifierAuth();
    chargerOffres();

    // Events Navigation Auth
    document.getElementById('link-register').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('form-login').parentElement.style.display = 'none';
        document.getElementById('register-box').style.display = 'block';
    });
    
    document.getElementById('link-login').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('register-box').style.display = 'none';
        document.getElementById('form-login').parentElement.style.display = 'block';
    });

    // Events Formulaires
    document.getElementById('form-login').addEventListener('submit', gererLogin);
    document.getElementById('form-register').addEventListener('submit', gererRegister);
    document.getElementById('btn-logout').addEventListener('click', gererLogout);

    // Events App
    document.getElementById('btn-upload-cv').addEventListener('click', uploaderCV);
    document.getElementById('select-offre').addEventListener('change', (e) => {
        currentOffreId = e.target.value;
        verifierPret();
    });
    
    document.getElementById('btn-demarrer').addEventListener('click', demarrerEntretien);
    document.getElementById('btn-terminer').addEventListener('click', terminerEntretien);
    document.getElementById('btn-retour-accueil').addEventListener('click', () => {
        document.getElementById('interface-resultat').style.display = 'none';
        document.getElementById('interface-preparation').style.display = 'block';
        document.getElementById('chat-container').innerHTML = '';
        currentEntretienId = null;
    });
});

// ============================================================
// AUTHENTIFICATION
// ============================================================
async function verifierAuth() {
    try {
        const res = await fetch('/api/me');
        if (res.ok) {
            const user = await res.json();
            currentUserId = user.id;
            afficherApp(user.prenom);
        } else {
            afficherAuth();
        }
    } catch (e) {
        afficherAuth();
    }
}

async function gererLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    if (res.ok) {
        verifierAuth();
    } else {
        const error = await res.json();
        alert(error.error);
    }
}

async function gererRegister(e) {
    e.preventDefault();
    const data = {
        nom: document.getElementById('reg-nom').value,
        prenom: document.getElementById('reg-prenom').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value
    };
    
    const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (res.ok) {
        verifierAuth();
    } else {
        const error = await res.json();
        alert(error.error);
    }
}

async function gererLogout() {
    await fetch('/api/logout', { method: 'POST' });
    currentUserId = null;
    afficherAuth();
}

// ============================================================
// UPLOAD ET PREPARATION
// ============================================================
async function chargerOffres() {
    const res = await fetch('/api/offres');
    const offres = await res.json();
    const select = document.getElementById('select-offre');
    
    offres.forEach(o => {
        const opt = document.createElement('option');
        opt.value = o.id;
        opt.textContent = o.titre;
        select.appendChild(opt);
    });
}

async function uploaderCV() {
    const fileInput = document.getElementById('input-cv');
    if (!fileInput.files[0]) return alert("Veuillez sélectionner un PDF");

    const status = document.getElementById('upload-status');
    status.textContent = "Envoi et analyse en cours...";
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch('/api/cv', { method: 'POST', body: formData });
        if (!res.ok) throw new Error((await res.json()).error);
        
        const data = await res.json();
        currentPdfId = data.id;
        status.textContent = "✅ CV téléchargé avec succès !";
        status.style.color = "green";
        verifierPret();
    } catch (e) {
        status.textContent = "❌ Erreur : " + e.message;
        status.style.color = "red";
    }
}

function verifierPret() {
    const btn = document.getElementById('btn-demarrer');
    btn.disabled = !(currentPdfId && currentOffreId);
}

// ============================================================
// GESTION UI AFFICHAGE
// ============================================================
function afficherAuth() {
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('app-section').style.display = 'none';
    document.getElementById('user-info').style.display = 'none';
}

function afficherApp(prenom) {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('app-section').style.display = 'block';
    document.getElementById('interface-preparation').style.display = 'block';
    document.getElementById('user-info').style.display = 'block';
    document.getElementById('user-name').textContent = "Bonjour, " + prenom;
}

function ajouterMessageUI(role, texte) {
    const container = document.getElementById('chat-container');
    const div = document.createElement('div');
    div.className = 'msg ' + (role === 'Système' ? 'msg-systeme' : 'msg-recruteur');
    div.innerHTML = `<strong>${role} :</strong> ${texte}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ============================================================
// ENTRETIEN EN DIRECT (WEBSOCKET + AUDIO)
// ============================================================
async function demarrerEntretien() {
    try {
        document.getElementById('btn-demarrer').textContent = "Création de la session...";
        document.getElementById('btn-demarrer').disabled = true;

        const res = await fetch('/api/entretiens', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pdf_id: currentPdfId, offre: currentOffreId })
        });
        
        if (!res.ok) throw new Error("Erreur de lancement de l'entretien");
        
        const data = await res.json();
        currentEntretienId = data.entretien_id;
        
        document.getElementById('interface-preparation').style.display = 'none';
        document.getElementById('interface-entretien').style.display = 'block';
        ajouterMessageUI("Système", "L'entretien a commencé. Gemini analyse votre CV...");

        await initLiveAudio(data.websocket_url);

    } catch (e) {
        console.error(e);
        alert("Impossible de démarrer l'entretien.");
        document.getElementById('btn-demarrer').textContent = "Démarrer l'entretien en direct";
        document.getElementById('btn-demarrer').disabled = false;
    }
}
async function initLiveAudio(websocketUrl) {
    arreterAudio();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    liveWs = new WebSocket(`${protocol}//${window.location.host}${websocketUrl}`);

    liveWs.onopen = async () => {
        console.log("WebSocket connecté");

        try {
            // Laisse le navigateur utiliser sa fréquence native (souvent 44100Hz ou 48000Hz)
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }

            micStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
        } catch (err) {
            console.error("Erreur Micro/AudioContext:", err);
            alert("Veuillez autoriser le microphone.");
            return;
        }

        const source = audioContext.createMediaStreamSource(micStream);
        scriptNode = audioContext.createScriptProcessor(4096, 1, 1);
        
        source.connect(scriptNode);
        scriptNode.connect(audioContext.destination);

        scriptNode.onaudioprocess = (e) => {
            if (liveWs && liveWs.readyState === WebSocket.OPEN) {
                // Ne pas envoyer le micro pendant que Gemini parle (évite le larsen/écho)
                if (isPlaying) return;

                const float32 = e.inputBuffer.getChannelData(0);

                // Conversion Float32 vers Int16 PCM
                const int16Array = new Int16Array(float32.length);
                for (let i = 0; i < float32.length; i++) {
                    let s = Math.max(-1, Math.min(1, float32[i]));
                    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }

                // Envoi avec la fréquence exacte du navigateur (audioContext.sampleRate)
                const uint8Array = new Uint8Array(int16Array.buffer);
                let binary = '';
                for (let i = 0; i < uint8Array.byteLength; i++) {
                    binary += String.fromCharCode(uint8Array[i]);
                }
                
                liveWs.send(JSON.stringify({ 
                    audio: btoa(binary),
                    sampleRate: audioContext.sampleRate 
                }));
            }
        };
    };

    liveWs.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.error) {
            console.error("Erreur WS:", msg.error);
        } else if (msg.type === 'audio') {
            playAudioChunk(msg.data);
        } else if (msg.type === 'text') {
            ajouterMessageUI("Recruteur", msg.data);
            sauvegarderTranscription([{ role: "recruteur", texte: msg.data }]);
        }
    };

    liveWs.onclose = () => arreterAudio();
}

async function playAudioChunk(base64Data) {
    if (!audioContext) return;
    if (audioContext.state === 'suspended') {
        await audioContext.resume();
    }
    
    isPlaying = true; // Empêche le micro de réémettre le son du haut-parleur

    const binaryStr = atob(base64Data);
    const len = binaryStr.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) bytes[i] = binaryStr.charCodeAt(i);
    
    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = audioContext.createBuffer(1, float32Array.length, 24000);
    audioBuffer.getChannelData(0).set(float32Array);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);

    if (nextPlayTime < audioContext.currentTime) nextPlayTime = audioContext.currentTime;
    source.start(nextPlayTime);
    nextPlayTime += audioBuffer.duration;

    // Réactive le micro une fois le paquet audio terminé
    setTimeout(() => {
        if (audioContext && audioContext.currentTime >= nextPlayTime) {
            isPlaying = false;
        }
    }, (nextPlayTime - audioContext.currentTime) * 1000);
}

function arreterAudio() {
    if (scriptNode) { scriptNode.disconnect(); scriptNode = null; }
    if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
    if (audioContext && audioContext.state !== 'closed') { audioContext.close(); audioContext = null; }
    if (liveWs && liveWs.readyState === WebSocket.OPEN) liveWs.close();
    liveWs = null;
    nextPlayTime = 0;
}

// ============================================================
// RESULTATS ET EVALUATION
// ============================================================
async function terminerEntretien() {
    arreterAudio();
    document.getElementById('btn-terminer').textContent = "Analyse en cours...";
    document.getElementById('btn-terminer').disabled = true;

    try {
        const res = await fetch(`/api/entretiens/${currentEntretienId}/terminer`, { method: 'POST' });
        const evalData = await res.json();
        
        document.getElementById('interface-entretien').style.display = 'none';
        document.getElementById('interface-resultat').style.display = 'block';
        document.getElementById('btn-terminer').textContent = "Terminer l'entretien";
        document.getElementById('btn-terminer').disabled = false;
        document.getElementById('btn-demarrer').textContent = "Démarrer l'entretien en direct";

        afficherResultat(evalData);
        
    } catch (e) {
        console.error(e);
        alert("Erreur lors de la récupération des résultats.");
    }
}

function afficherResultat(data) {
    const container = document.getElementById('evaluation-content');
    if (data.error) {
        container.innerHTML = `<p style="color:red">${data.error}</p>`;
        return;
    }

    container.innerHTML = `
        <div class="score-banniere">Note Globale : ${data.note_globale} / 100</div>
        <p><strong>Verdict :</strong> ${data.verdict}</p>
        
        <div class="eval-grid">
            <div class="eval-box">
                <h4>Compétences détaillées</h4>
                <ul>
                    <li>Communication : ${data.communication}/10</li>
                    <li>Technique : ${data.competences_techniques}/10</li>
                    <li>Motivation : ${data.motivation}/10</li>
                </ul>
            </div>
            <div class="eval-box">
                <h4>Points forts</h4>
                <ul>${data.points_forts.map(p => `<li>${p}</li>`).join('')}</ul>
            </div>
        </div>
        
        <div class="eval-box" style="margin-top: 1rem">
            <h4>Axes d'amélioration</h4>
            <ul>${data.axes_amelioration.map(a => `<li>${a}</li>`).join('')}</ul>
        </div>
    `;
}

async function sauvegarderTranscription(messages) {
    if (!currentEntretienId) return;
    try {
        await fetch(`/api/entretiens/${currentEntretienId}/transcription`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages })
        });
    } catch (e) {
        console.error(e);
    }
}