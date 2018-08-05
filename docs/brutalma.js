// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3.0
// Copyright (C) 2018  Nguyễn Gia Phong
const PERIGON = Math.PI * 2;
const TANGO = {'a': '#fce94f', 'b': '#edd400', 'c': '#c4a000',  // Butter
               'd': '#fcaf3e', 'e': '#f57900', 'f': '#ce5c00',  // Orange
               'g': '#e9b96e', 'h': '#c17d11', 'i': '#8f5902',  // Chocolate
               'j': '#8ae234', 'k': '#73d216', 'l': '#4e9a06',  // Chameleon
               'm': '#729fcf', 'n': '#3465a4', 'o': '#204a87',  // Sky Blue
               'p': '#ad7fa8', 'q': '#75507b', 'r': '#5c3566',  // Plum
               's': '#ef2929', 't': '#cc0000', 'u': '#a40000',  // Scarlet Red
               'v': '#eeeeec', 'w': '#d3d7cf', 'x': '#babdb6',  // Aluminium
               'y': '#888a85', 'z': '#555753', '0': '#2e3436'};
var mw, mh;     // maze width and height in grids

// Resize canvas to fit page.
function resizeCanvas(canvas) {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

// Draw on the given canvas a c-colored regular n-gon with circumradius of R,
// center point I(x, y) and corner A that angle of vector IA is r (in radians).
function drawPolygon(canvas, n, c, x, y, r, R) {
    var ctx = canvas.getContext('2d');
    ctx.beginPath();
    r = r * Math.PI / 180 % PERIGON;
    ctx.moveTo(x + R*Math.cos(r), y + R*Math.sin(r));
    for (var i = 1; i < n; i++) {
        r += PERIGON / n;
        ctx.lineTo(x + R*Math.cos(r), y + R*Math.sin(r));
    }
    ctx.closePath();
    ctx.fillStyle = TANGO[c];
    ctx.fill();
}

// Draw the maze, hero, enemies and bullets of the given frame.
function drawFrame(canvas, frame) {
    var cw = canvas.width, ch = canvas.height;
    var maze = frame.m;
    if (maze) {
        mw = maze[0].length;
        mh = maze.length;
    }
    unit = Math.min(cw / (mw + 1), ch / (mh + 1));
    eR = unit / Math.sqrt(2);
    hR = unit * 2 / Math.pow(27, 0.25);
    bR = unit / 4;

    var hero = frame.h;
    var x0 = cw/2 - hero[1]/100*unit, y0 = ch/2 - hero[2]/100*unit;

    canvas.getContext('2d').clearRect(0, 0, cw, ch);
    if (maze)
    for (var row = 0; row < mh; row++)
        for (var column = 0; column < mw; column++)
            if (maze[row][column] != '0') {
                var x = x0 + column*unit, y = y0 + row*unit;
                var ctx = canvas.getContext('2d');
                ctx.fillStyle = TANGO[maze[row][column]];
                ctx.fillRect(x, y, unit + 1, unit + 1);
            }

    if (frame.e)
        for (let enemy of frame.e)
            drawPolygon(canvas, 4, enemy[0], x0 + enemy[1]/100*unit,
                        y0 + enemy[2]/100*unit, enemy[3], eR);
    drawPolygon(canvas, 4 - hero[5], hero[0], cw / 2, ch / 2, hero[3], hR);

    if (frame.b)
        for (let bullet of frame.b)
            drawPolygon(canvas, 5, bullet[0], x0 + bullet[1]/100*unit,
                        y0 + bullet[2]/100*unit, bullet[3], bR);
}

// Recursive function to loop with window.setTimeout.
function playRecord(canvas, record, index) {
    if (index >= record.length) {
        document.title = 'Brutal Maze record player';
        document.getElementById('input').style.display = '';
        return;
    }

    frame = record[index];
    document.title = `Score: ${frame.s}`;
    setTimeout(function () {
        drawFrame(canvas, frame);
        playRecord(canvas, record, index + 1);
    }, frame.t);
}

// Fetch JSON record and parse to playRecord.
function playJSON() {
    fetch(document.getElementById('record').value).then(function(res) {
        return res.json();
    }).then(function(record) {
        document.getElementById('input').style.display = 'none';
        playRecord(document.getElementById('canvas'), record, 0);
    }).catch(error => alert(error));
}
// @license-end
