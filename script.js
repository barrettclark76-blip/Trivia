// 1. Import Firebase modules from the CDN (All versions must match 12.10.0)
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.10.0/firebase-app.js";
import { getDatabase, ref, set, get, child } from "https://www.gstatic.com/firebasejs/12.10.0/firebase-database.js";

// 2. Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyD2gatwKx8VILOxCJoQ2ebAJ8zCceMy918", // <-- PUT YOUR REAL API KEY HERE
    authDomain: "triviality-7817d.firebaseapp.com",
    databaseURL: "https://triviality-7817d-default-rtdb.firebaseio.com",
    projectId: "triviality-7817d",
    storageBucket: "triviality-7817d.firebasestorage.app",
    messagingSenderId: "369507448493",
    appId: "1:369507448493:web:a38ea5b3fa993c9433f824"
};

// 3. Initialize Firebase Application and Database
const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

// Game State Variables
let myNickname = "";
let currentRoom = "";
let isHost = false;
let currentPhase = "";
let hasSubmitted = false;

// Dummy Trivia Database (You can connect a real API later)
const triviaDB = {
    "Sports": [{ q: "How many points is a touchdown worth?", a: "6" }],
    "Geography": [{ q: "What is the capital of France?", a: "paris" }],
    "Arts": [{ q: "Who painted the Mona Lisa?", a: "da vinci" }],
    "Science": [{ q: "What planet is known as the Red Planet?", a: "mars" }],
    "History": [{ q: "Who was the first US President?", a: "washington" }],
    "General Knowledge": [{ q: "How many days are in a leap year?", a: "366" }]
};
const categories = Object.keys(triviaDB);

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const screens = {
        main: document.getElementById("main-menu"),
        lobby: document.getElementById("game-lobby"),
        active: document.getElementById("game-active")
    };
    const phases = {
        wheel: document.getElementById("phase-wheel"),
        countdown: document.getElementById("phase-countdown"),
        question: document.getElementById("phase-question"),
        leaderboard: document.getElementById("phase-leaderboard")
    };

    function showScreen(screenName) {
        Object.values(screens).forEach(s => s.classList.add('hidden'));
        screens[screenName].classList.remove('hidden');
    }

    function showPhase(phaseName) {
        Object.values(phases).forEach(p => p.classList.add('hidden'));
        if(phaseName) phases[phaseName].classList.remove('hidden');
    }

    // --- LOBBY LOGIC ---
    document.getElementById("btn-create-private").addEventListener("click", () => {
        myNickname = document.getElementById("nickname").value.trim();
        if (!myNickname) return alert("Enter nickname!");

        currentRoom = Math.random().toString(36).substring(2, 7).toUpperCase();
        isHost = true;

        set(ref(db, `rooms/${currentRoom}`), {
            host: myNickname,
            state: 'lobby',
            questionCount: 0,
            players: { [myNickname]: { score: 0, answered: false } }
        }).then(() => {
            document.getElementById("display-room-code").innerText = currentRoom;
            showScreen('lobby');
            listenToRoom(); // Start real-time sync
        });
    });

    document.getElementById("btn-join-private").addEventListener("click", () => {
        myNickname = document.getElementById("nickname").value.trim();
        const code = document.getElementById("room-code").value.trim().toUpperCase();
        if (!myNickname || !code) return alert("Enter nickname and code!");

        get(child(ref(db), `rooms/${code}`)).then((snapshot) => {
            if (snapshot.exists() && snapshot.val().state === 'lobby') {
                currentRoom = code;
                isHost = false;
                
                update(ref(db, `rooms/${currentRoom}/players/${myNickname}`), { 
                    score: 0, answered: false 
                }).then(() => {
                    document.getElementById("display-room-code").innerText = currentRoom;
                    showScreen('lobby');
                    listenToRoom(); // Start real-time sync
                });
            } else {
                alert("Room not found or game already started.");
            }
        });
    });

    // --- REAL-TIME SYNC (THE MAGIC) ---
    function listenToRoom() {
        const roomRef = ref(db, `rooms/${currentRoom}`);
        
        onValue(roomRef, (snapshot) => {
            const data = snapshot.val();
            if (!data) {
                // Host left and deleted room
                alert("Room closed!");
                location.reload();
                return;
            }

            // Update Player List
            const playersList = document.getElementById("players-list");
            playersList.innerHTML = "";
            let playerCount = 0;
            for (let player in data.players) {
                playerCount++;
                const li = document.createElement("li");
                li.innerText = `${player} - Score: ${data.players[player].score}`;
                playersList.appendChild(li);
            }

            // Show Start Button for Host if >= 2 players
            if (isHost && data.state === 'lobby') {
                const startBtn = document.getElementById("btn-start-game");
                if (playerCount >= 2) {
                    startBtn.classList.remove("hidden");
                } else {
                    startBtn.classList.add("hidden");
                }
            }

            // --- GAME STATE MACHINE UI ---
            if (data.state !== 'lobby' && data.state !== currentPhase) {
                currentPhase = data.state;
                showScreen('active');

                if (data.state === 'spinning') {
                    showPhase('wheel');
                    // Simple visual effect for everyone
                    let spins = 0;
                    const spinInterval = setInterval(() => {
                        document.getElementById("wheel-text").innerText = categories[spins % categories.length];
                        spins++;
                    }, 100);
                    setTimeout(() => { 
                        clearInterval(spinInterval);
                        document.getElementById("wheel-text").innerText = data.currentCategory;
                    }, 2500);
                } 
                else if (data.state === 'countdown') {
                    showPhase('countdown');
                    let count = 3;
                    document.getElementById("countdown-text").innerText = count;
                    const countTimer = setInterval(() => {
                        count--;
                        if (count > 0) document.getElementById("countdown-text").innerText = count;
                        else clearInterval(countTimer);
                    }, 1000);
                }
                else if (data.state === 'question') {
                    showPhase('question');
                    hasSubmitted = false;
                    document.getElementById("current-category").innerText = data.currentCategory;
                    document.getElementById("question-text").innerText = data.currentQuestion;
                    document.getElementById("answer-input").value = "";
                    document.getElementById("answer-input").disabled = false;
                    document.getElementById("btn-submit-answer").disabled = false;
                    
                    // Local timer for UI
                    let timeLeft = 30;
                    document.getElementById("timer-text").innerText = timeLeft;
                    const qTimer = setInterval(() => {
                        timeLeft--;
                        if (timeLeft >= 0) document.getElementById("timer-text").innerText = timeLeft;
                        if (currentPhase !== 'question') clearInterval(qTimer);
                    }, 1000);
                }
                else if (data.state === 'leaderboard') {
                    showPhase('leaderboard');
                    // Check if player didn't answer and deduct points
                    if (!hasSubmitted) {
                        updatePlayerScore(-2); 
                        document.getElementById("round-result-msg").innerText = "Time's up! -2 Points";
                    }

                    const lbList = document.getElementById("leaderboard-list");
                    lbList.innerHTML = "";
                    // Sort players by score
                    const sortedPlayers = Object.entries(data.players).sort((a, b) => b[1].score - a[1].score);
                    sortedPlayers.forEach(([name, info]) => {
                        const li = document.createElement("li");
                        li.innerText = `${name}: ${info.score} pts`;
                        lbList.appendChild(li);
                    });
                }
                else if (data.state === 'ended') {
                    showPhase('leaderboard');
                    document.getElementById("round-result-msg").innerText = "GAME OVER! Final Standings";
                    setTimeout(() => location.reload(), 8000); // Reset after 8s
                }
            }
        });
    }

    // --- HOST CONTROLS (Driving the game) ---
    document.getElementById("btn-start-game").addEventListener("click", () => {
        runGameLoop(1);
    });

    function runGameLoop(questionNumber) {
        if (questionNumber > 10) {
            update(ref(db, `rooms/${currentRoom}`), { state: 'ended' });
            return;
        }

        // 1. Wheel Spin
        const randomCat = categories[Math.floor(Math.random() * categories.length)];
        // Pick a random question from that category
        const qData = triviaDB[randomCat][0]; 

        update(ref(db, `rooms/${currentRoom}`), { 
            state: 'spinning',
            currentCategory: randomCat,
            currentQuestion: qData.q,
            correctAnswer: qData.a,
            questionCount: questionNumber
        });

        // 2. Countdown
        setTimeout(() => {
            update(ref(db, `rooms/${currentRoom}`), { state: 'countdown' });
            
            // 3. Question Phase
            setTimeout(() => {
                update(ref(db, `rooms/${currentRoom}`), { state: 'question' });
                
                // 4. End Question / Leaderboard Phase (After 30 seconds)
                setTimeout(() => {
                    update(ref(db, `rooms/${currentRoom}`), { state: 'leaderboard' });
                    
                    // 5. Loop to next question (After 5 seconds on leaderboard)
                    setTimeout(() => {
                        runGameLoop(questionNumber + 1);
                    }, 5000);

                }, 30000); // 30 second answering time
            }, 3000); // 3 second countdown
        }, 3000); // 3 seconds spinning
    }

    // --- ANSWER LOGIC ---
    document.getElementById("btn-submit-answer").addEventListener("click", () => {
        if (hasSubmitted) return;
        hasSubmitted = true;
        document.getElementById("answer-input").disabled = true;
        document.getElementById("btn-submit-answer").disabled = true;

        const rawAns = document.getElementById("answer-input").value.trim().toLowerCase();
        
        // Fetch correct answer to check
        get(child(ref(db), `rooms/${currentRoom}/correctAnswer`)).then((snapshot) => {
            const correctAns = snapshot.val().toLowerCase();
            if (rawAns === correctAns) {
                document.getElementById("timer-text").innerText = "CORRECT!";
                updatePlayerScore(5);
            } else {
                document.getElementById("timer-text").innerText = "WRONG!";
                updatePlayerScore(-5);
            }
        });
    });

    function updatePlayerScore(points) {
        get(child(ref(db), `rooms/${currentRoom}/players/${myNickname}/score`)).then((snapshot) => {
            const currentScore = snapshot.val() || 0;
            update(ref(db, `rooms/${currentRoom}/players/${myNickname}`), {
                score: currentScore + points
            });
        });
    }
});
