document.addEventListener("DOMContentLoaded", () => {
    // Input elements
    const nicknameInput = document.getElementById("nickname");
    const roomCodeInput = document.getElementById("room-code");
    const displayRoomCode = document.getElementById("display-room-code");

    // Button elements
    const btnMatchmake = document.getElementById("btn-matchmake");
    const btnCreatePrivate = document.getElementById("btn-create-private");
    const btnJoinPrivate = document.getElementById("btn-join-private");
    const btnLeave = document.getElementById("btn-leave");

    // Screens
    const mainMenu = document.getElementById("main-menu");
    const gameLobby = document.getElementById("game-lobby");

    // Helper function to switch screens
    function showScreen(screenElement) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        screenElement.classList.add('active');
    }

    // Helper function to validate nickname
    function getNickname() {
        const name = nicknameInput.value.trim();
        if (!name) {
            alert("Please enter a nickname first!");
            return null;
        }
        return name;
    }

    // Event: Matchmaking
    btnMatchmake.addEventListener("click", () => {
        const nickname = getNickname();
        if (!nickname) return;

        console.log(`${nickname} is searching for a public match...`);
        // TODO: Backend logic to find an open game goes here
        
        displayRoomCode.innerText = "Public Match";
        showScreen(gameLobby);
    });

    // Event: Create Private Game
    btnCreatePrivate.addEventListener("click", () => {
        const nickname = getNickname();
        if (!nickname) return;

        // Generate a random 5-letter room code for UI purposes
        const newCode = Math.random().toString(36).substring(2, 7).toUpperCase();
        console.log(`${nickname} created private room: ${newCode}`);
        
        // TODO: Backend logic to create a room in the database goes here

        displayRoomCode.innerText = newCode;
        showScreen(gameLobby);
    });

    // Event: Join Private Game
    btnJoinPrivate.addEventListener("click", () => {
        const nickname = getNickname();
        if (!nickname) return;

        const code = roomCodeInput.value.trim().toUpperCase();
        if (!code) {
            alert("Please enter a room code!");
            return;
        }

        console.log(`${nickname} is attempting to join room: ${code}`);
        
        // TODO: Backend logic to check if room exists and join it goes here

        displayRoomCode.innerText = code;
        showScreen(gameLobby);
    });

    // Event: Leave Lobby (Go back to main menu)
    btnLeave.addEventListener("click", () => {
        // TODO: Backend logic to disconnect from the room goes here
        showScreen(mainMenu);
    });
});
