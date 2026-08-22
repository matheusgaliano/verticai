import React from 'react';

/**
 * Ícone oficial do VerticAI — camadas decrescentes com um ponto no topo,
 * remetendo ao edital verticalizado. Usa currentColor: a cor vem do CSS do
 * elemento pai (por padrão, o tom de destaque esmeralda do tema).
 */
export default function Logo({ size = 24, className = '', style = {} }) {
    return (
        <svg
            viewBox="0 0 240 240"
            width={size}
            height={size}
            className={className}
            style={{ color: 'var(--accent)', flexShrink: 0, ...style }}
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
        >
            <rect x="32" y="152" width="76" height="14" rx="3" fill="currentColor" />
            <rect x="44" y="130" width="52" height="14" rx="3" fill="currentColor" />
            <rect x="56" y="108" width="28" height="14" rx="3" fill="currentColor" />
            <circle cx="70" cy="88" r="6" fill="currentColor" />
        </svg>
    );
}
