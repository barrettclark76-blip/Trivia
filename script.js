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

// 4. Main Menu and Lobby Logic
document.addEventListener("DOMContentLoaded", () => {
    const nicknameInput = document.getElementById("nickname");
    const roomCodeInput = document.getElementById("room-code");
    const displayRoomCode = document.getElementById("display-room-code");
    const lobbyStatus = document.getElementById("lobby-status");

    const btnCreatePrivate = document.getElementById("btn-create-private");
    const btnJoinPrivate = document.getElementById("btn-join-private");
    const btnLeave = document.getElementById("btn-leave");

    const mainMenu = document.getElementById("main-menu");
    const gameLobby = document.getElementById("game-lobby");

    function showScreen(screenElement) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        screenElement.classList.add('active');
    }

    function getNickname() {
        const name = nicknameInput.value.trim();
        if (!name) {
            alert("Please enter a nickname first!");
            return null;
        }
        return name;
    }

    // CREATE a private room
    btnCreatePrivate.addEventListener("click", () => {
        const nickname = getNickname();
        if (!nickname) return;

        // Generate a random 5-letter room code
        const newCode = Math.random().toString(36).substring(2, 7).toUpperCase();
        
        // Save the room to Firebase
        set(ref(db, 'rooms/' + newCode), {
            host: nickname,
            status: 'waiting',
            players: {
                [nickname]: { score: 0, isHost: true }
            }
        }).then(() => {
            displayRoomCode.innerText = newCode;
            lobbyStatus.innerText = "Waiting for players...";
            showScreen(gameLobby);
        }).catch((error) => {
            alert("Error creating room: " + error.message);
        });
    });

    // JOIN a private room
    btnJoinPrivate.addEventListener("click", () => {
        const nickname = getNickname();
        if (!nickname) return;

        const code = roomCodeInput.value.trim().toUpperCase();
        if (!code) {
            alert("Please enter a room code!");
            return;
        }

        // Check Firebase to see if the room exists
        const dbRef = ref(db);
        get(child(dbRef, `rooms/${code}`)).then((snapshot) => {
            if (snapshot.exists()) {
                // Room exists! Add player to the room
                set(ref(db, `rooms/${code}/players/${nickname}`), {
                    score: 0,
                    isHost: false
                }).then(() => {
                    displayRoomCode.innerText = code;
                    lobbyStatus.innerText = "Joined! Waiting for host to start...";
                    showScreen(gameLobby);
                });
            } else {
                alert("Room not found. Check the code and try again.");
            }
        }).catch((error) => {
            alert("Error joining room: " + error.message);
        });
    });

    // LEAVE Lobby
    btnLeave.addEventListener("click", () => {
        showScreen(mainMenu);
    });
});
