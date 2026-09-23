document.addEventListener('DOMContentLoaded', () => {
    
    const focusables = Array.from(document.querySelectorAll('.focusable'));
    
    const groups = [
        document.querySelectorAll('.nav-item'),
        document.querySelectorAll('.nav-icons .focusable'),
        document.querySelectorAll('.btn'),
        document.querySelectorAll('.app-card')
    ];
    let currentGroupIndex = 3; 
    let itemIndexInGroup = 0;

    function updateFocus() {
        focusables.forEach(el => el.classList.remove('focused'));
        const currentGroup = groups[currentGroupIndex];
        
        if (currentGroup && currentGroup.length > 0) {
            if (itemIndexInGroup >= currentGroup.length) {
                itemIndexInGroup = currentGroup.length - 1;
            }
            if (itemIndexInGroup < 0) {
                itemIndexInGroup = 0;
            }
            const focusedEl = currentGroup[itemIndexInGroup];
            focusedEl.classList.add('focused');
            focusedEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
        }
    }

    function executeCommand(command) {
        switch (command) {
            case 'up':
                if (currentGroupIndex > 0) {
                    currentGroupIndex--;
                    updateFocus();
                }
                break;
            case 'down':
                if (currentGroupIndex < groups.length - 1) {
                    currentGroupIndex++;
                    updateFocus();
                }
                break;
            case 'left':
                if (itemIndexInGroup > 0) {
                    itemIndexInGroup--;
                    updateFocus();
                }
                break;
            case 'right':
                const currentGroup = groups[currentGroupIndex];
                if (itemIndexInGroup < currentGroup.length - 1) {
                    itemIndexInGroup++;
                    updateFocus();
                }
                break;
            case 'enter':
                const focusedEl = groups[currentGroupIndex][itemIndexInGroup];
                if (focusedEl) {
                    if (focusedEl.getAttribute('data-action') === 'shutdown') {
                        fetch('/shutdown');
                        return;
                    }
                    const url = focusedEl.getAttribute('data-url');
                    if (url) {
                        window.location.href = url;
                    }
                }
                break;
        }
    }

    updateFocus();

    
    focusables.forEach((el, index) => {
        el.addEventListener('mouseenter', () => {
            
            for (let g = 0; g < groups.length; g++) {
                const elsInGroup = Array.from(groups[g]);
                const i = elsInGroup.indexOf(el);
                if (i !== -1) {
                    currentGroupIndex = g;
                    itemIndexInGroup = i;
                    updateFocus();
                    break;
                }
            }
        });

        el.addEventListener('click', () => {
            executeCommand('enter');
        });
    });

    let lastCommandTime = 0;
    function handleCommand(cmd) {
        const now = Date.now();
        if (now - lastCommandTime < 150) return; 
        lastCommandTime = now;
        executeCommand(cmd);
    }

    window.addEventListener('keydown', (e) => {
        let cmd = null;
        if (e.key === 'ArrowUp') cmd = 'up';
        if (e.key === 'ArrowDown') cmd = 'down';
        if (e.key === 'ArrowLeft') cmd = 'left';
        if (e.key === 'ArrowRight') cmd = 'right';
        if (e.key === 'Enter') cmd = 'enter';
        
        if (cmd) {
            e.preventDefault();
            handleCommand(cmd);
        }
    });

    
    

    
    const showIds = [82, 169, 2993, 43687, 84, 2]; 
    let showsData = [];
    let currentShowIndex = 0;

    async function fetchShows() {
        try {
            for (let id of showIds) {
                const res = await fetch(`https://api.tvmaze.com/shows/${id}`);
                if (res.ok) {
                    const data = await res.json();
                    showsData.push(data);
                }
            }
            if (showsData.length > 0) {
                updateBanner(showsData[0]);
                setInterval(cycleBanner, 10000); 
            }
        } catch (e) {
            console.error("Error fetching shows from TVMaze:", e);
        }
    }

    function updateBanner(show) {
        const bg = document.getElementById('banner-bg');
        const title = document.getElementById('banner-title');
        const desc = document.getElementById('banner-desc');
        
        if (show.image && show.image.original) {
            bg.style.backgroundImage = `url('${show.image.original}')`;
        }
        title.textContent = show.name;
        
        let cleanSummary = show.summary ? show.summary.replace(/<\/?[^>]+(>|$)/g, "") : "";
        if (cleanSummary.length > 250) cleanSummary = cleanSummary.substring(0, 250) + '...';
        desc.textContent = cleanSummary;
    }

    function cycleBanner() {
        if (showsData.length === 0) return;
        currentShowIndex = (currentShowIndex + 1) % showsData.length;
        updateBanner(showsData[currentShowIndex]);
    }

    function updateClock() {
        const clockEl = document.getElementById('clock');
        if (clockEl) {
            const now = new Date();
            let hours = now.getHours();
            let minutes = now.getMinutes();
            const ampm = hours >= 12 ? 'PM' : 'AM';
            hours = hours % 12;
            hours = hours ? hours : 12; 
            minutes = minutes < 10 ? '0' + minutes : minutes;
            clockEl.textContent = hours + ':' + minutes + ' ' + ampm;
        }
    }
    setInterval(updateClock, 1000);
    updateClock();

    fetchShows();
});
