/*
 * Visual analysis page: eval evolution chart, ranked eval swings, board moments.
 */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    function loadData() {
        const movesEl = document.getElementById('ai-moves-data');
        const pgnEl = document.getElementById('ai-pgn-source');
        if (!movesEl) return null;
        try {
            return {
                moves: JSON.parse(movesEl.textContent),
                pgn: pgnEl ? pgnEl.textContent.trim() : ''
            };
        } catch (e) {
            console.warn('ai_analysis_enhancements: bad moves JSON', e);
            return null;
        }
    }

    function fenSequenceFromPgn(pgn) {
        const fens = [];
        const replay = new Chess();
        fens.push(replay.fen());
        if (!pgn) return fens;

        const loader = new Chess();
        let history;
        try {
            const ok = loader.load_pgn(pgn, { sloppy: true });
            if (!ok) return fens;
            history = loader.history({ verbose: true });
        } catch (e) {
            console.warn('ai_analysis_enhancements: PGN load failed', e);
            return fens;
        }
        for (const move of history) {
            replay.move(move);
            fens.push(replay.fen());
        }
        return fens;
    }

    function evalToPawns(cp) {
        if (cp === null || cp === undefined) return null;
        if (cp >= 998) return 10;
        if (cp <= -998) return -10;
        return Math.max(-10, Math.min(10, cp / 100.0));
    }

    function formatEval(cp) {
        if (cp === null || cp === undefined) return '—';
        if (cp >= 998) return '+M';
        if (cp <= -998) return '−M';
        return (cp > 0 ? '+' : '') + (cp / 100.0).toFixed(2);
    }

    function moverPerspectiveDeltaCp(m) {
        const before = (m.eval_before === null || m.eval_before === undefined) ? 0 : m.eval_before;
        const after = (m.eval_after === null || m.eval_after === undefined) ? 0 : m.eval_after;
        return m.is_white ? (after - before) : (before - after);
    }

    function absEvalSwingCp(m) {
        const before = (m.eval_before === null || m.eval_before === undefined) ? 0 : m.eval_before;
        const after = (m.eval_after === null || m.eval_after === undefined) ? 0 : m.eval_after;
        return Math.abs(after - before);
    }

    /** Largest absolute engine jumps (centipawns), White’s perspective before/after. */
    function rankTopAbsSwings(moves, n, minSwingCp) {
        const arr = moves.map((m, i) => ({ index: i, m, swing: absEvalSwingCp(m) }))
            .filter(x => x.swing >= minSwingCp);
        arr.sort((a, b) => b.swing - a.swing);
        return arr.slice(0, n);
    }

    /** Worst half-moves for the side that played (centipawn loss from mover POV). */
    function pickWorstMomentsForMover(moves, maxCount, minLossCp) {
        const scored = moves.map((m, i) => ({ index: i, delta: moverPerspectiveDeltaCp(m) }));
        scored.sort((a, b) => a.delta - b.delta);
        return scored
            .filter(s => s.delta <= -minLossCp)
            .slice(0, maxCount)
            .sort((a, b) => a.index - b.index)
            .map(s => s.index);
    }

    function renderEvalGraph(moves) {
        const canvas = document.getElementById('ai-eval-chart');
        if (!canvas || typeof Chart === 'undefined') return;

        const labels = moves.map(m => m.move_number + (m.is_white ? 'w' : 'b'));
        const data = moves.map(m => evalToPawns(m.eval_after));
        const swingHighlights = new Set(rankTopAbsSwings(moves, 7, 40).map(x => x.index));

        new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    data,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13,110,253,0.12)',
                    fill: true,
                    tension: 0.25,
                    pointRadius: (ctx) => swingHighlights.has(ctx.dataIndex) ? 7 : 2,
                    pointBackgroundColor: (ctx) => swingHighlights.has(ctx.dataIndex) ? '#dc3545' : '#0d6efd',
                    spanGaps: true
                }]
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => ctx.parsed.y === null
                                ? '—'
                                : (ctx.parsed.y > 0 ? '+' : '') + ctx.parsed.y.toFixed(2) + ' pawns'
                        }
                    }
                },
                scales: {
                    y: {
                        min: -10,
                        max: 10,
                        grid: { color: '#eee' },
                        ticks: { callback: v => v > 0 ? '+' + v : v }
                    },
                    x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } }
                }
            }
        });
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    function renderSwingRankings(moves) {
        const ol = document.getElementById('ai-swing-rankings');
        if (!ol) return;

        const top = rankTopAbsSwings(moves, 12, 30);
        if (top.length === 0) {
            ol.innerHTML = '<li class="list-group-item text-muted small">No large eval swings detected for this game.</li>';
            return;
        }

        ol.innerHTML = '';
        top.forEach(({ m, swing }) => {
            const ply = m.move_number + (m.is_white ? '.' : '...');
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2';
            li.innerHTML =
                '<div><span class="font-monospace text-muted">' + escapeHtml(ply) + '</span> ' +
                '<strong>' + escapeHtml(m.move_san || '') + '</strong>' +
                (m.best_move_san
                    ? ' <span class="text-muted small">(engine ' + escapeHtml(m.best_move_san) + ')</span>'
                    : '') +
                '</div><div class="font-monospace small text-md-end text-nowrap">' +
                formatEval(m.eval_before) + ' → ' + formatEval(m.eval_after) +
                ' <span class="text-danger fw-semibold ms-1">' + (swing / 100).toFixed(1) + ' pawn swing</span></div>';
            ol.appendChild(li);
        });
    }

    function sanToSquares(fen, san) {
        try {
            const c = new Chess(fen);
            const mv = c.move(san, { sloppy: true });
            return mv ? { from: mv.from, to: mv.to } : null;
        } catch (e) {
            return null;
        }
    }

    function narrationFor(move, before, after) {
        const cls = move.classification || 'mistake';
        const best = move.best_move_san;
        const dropPawns = Math.abs(evalToPawns(after) - evalToPawns(before)).toFixed(1);

        if (cls === 'blunder') {
            return 'A decisive blunder. ' +
                (best ? '<strong>' + escapeHtml(best) + '</strong> was sharply better. ' : '') +
                'Eval swung by about ' + dropPawns + ' pawns. ' +
                '<em>Lesson: pause and re-check tactical motifs before committing to a move.</em>';
        }
        if (cls === 'mistake') {
            return 'A significant mistake. ' +
                (best ? 'Engine prefers <strong>' + escapeHtml(best) + '</strong>. ' : '') +
                '<em>Lesson: when an engine alternative is available, candidate-move comparison usually finds it.</em>';
        }
        return 'An inaccuracy — the position is still playable, but ' +
            (best ? '<strong>' + escapeHtml(best) + '</strong> was tighter.' : 'a sharper continuation existed.');
    }

    function renderCriticalMoments(moves, fens) {
        const container = document.getElementById('ai-critical-moments');
        if (!container) return;

        const critIndices = pickWorstMomentsForMover(moves, 5, 75);
        if (critIndices.length === 0) {
            container.innerHTML =
                '<p class="text-muted small mb-0">No decisive losses from the mover’s perspective at this threshold — try the move list on Initial analysis.</p>';
            return;
        }

        critIndices.forEach((idx, cardI) => {
            const m = moves[idx];
            const fen = fens[idx] || 'start';
            const side = m.is_white ? 'white' : 'black';
            const cls = m.classification || 'mistake';
            const sev = (cls === 'blunder') ? 'blunder'
                : (cls === 'mistake') ? 'mistake'
                    : 'inaccuracy';
            const sevLabel = sev[0].toUpperCase() + sev.slice(1);
            const boardId = 'ai-board-' + cardI;
            const lossCp = Math.abs(Math.min(0, moverPerspectiveDeltaCp(m)));

            const col = document.createElement('div');
            col.className = 'col-lg-4 col-md-6';
            col.innerHTML =
                '<div class="card border-0 shadow-sm h-100">' +
                    '<div class="card-header bg-white d-flex justify-content-between align-items-center">' +
                        '<div>' +
                            '<div class="fw-semibold">Move ' + m.move_number + ' — ' + sevLabel + '</div>' +
                            '<div class="text-muted small">' + (side === 'black' ? 'Black to move' : 'White to move') +
                            ' · −' + lossCp.toFixed(0) + ' cp for mover</div>' +
                        '</div>' +
                        '<span class="ai-sev ai-sev-' + sev + '">' + sev + '</span>' +
                    '</div>' +
                    '<div class="card-body">' +
                        '<div id="' + boardId + '" style="width:100%; max-width:300px; margin:0 auto;"></div>' +
                        '<div class="d-flex justify-content-center gap-2 flex-wrap mt-3">' +
                            '<span class="text-muted small">Played</span>' +
                            '<span class="ai-move-pill played">' + escapeHtml(m.move_san || '') + '</span>' +
                            (m.best_move_san
                                ? '<span class="text-muted small ms-2">Engine</span>' +
                                  '<span class="ai-move-pill best">' + escapeHtml(m.best_move_san) + '</span>'
                                : '') +
                        '</div>' +
                        '<div class="text-center small text-muted mt-2">' +
                            'Eval ' + formatEval(m.eval_before) + ' → ' +
                            '<span class="text-danger fw-semibold">' + formatEval(m.eval_after) + '</span>' +
                            (m.centipawn_loss != null
                                ? ' · CPL ' + Number(m.centipawn_loss).toFixed(0)
                                : '') +
                        '</div>' +
                    '</div>' +
                    '<div class="card-footer bg-light small">' +
                        narrationFor(m, m.eval_before, m.eval_after) +
                    '</div>' +
                '</div>';
            container.appendChild(col);

            Chessboard(boardId, {
                position: fen,
                pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
                showNotation: false,
                orientation: side
            });

            setTimeout(() => {
                const played = sanToSquares(fen, m.move_san);
                const best = m.best_move_san ? sanToSquares(fen, m.best_move_san) : null;
                if (played) {
                    $('#' + boardId + ' .square-' + played.from).addClass('ai-hl-played-from');
                    $('#' + boardId + ' .square-' + played.to).addClass('ai-hl-played-to');
                }
                if (best) {
                    $('#' + boardId + ' .square-' + best.from).addClass('ai-hl-best-from');
                    $('#' + boardId + ' .square-' + best.to).addClass('ai-hl-best-to');
                }
            }, 80);
        });
    }

    ready(function () {
        if (typeof Chess === 'undefined' || typeof Chessboard === 'undefined') {
            console.warn('ai_analysis_enhancements: chess.js / chessboard.js not loaded');
            return;
        }
        const data = loadData();
        if (!data) return;
        const fens = fenSequenceFromPgn(data.pgn);
        try { renderSwingRankings(data.moves); }
        catch (e) { console.warn('swing rankings failed', e); }
        try { renderEvalGraph(data.moves); }
        catch (e) { console.warn('eval graph render failed', e); }
        try { renderCriticalMoments(data.moves, fens); }
        catch (e) { console.warn('critical moments render failed', e); }
    });
})();
