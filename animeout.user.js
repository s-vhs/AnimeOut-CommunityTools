// ==UserScript==
// @name         AnimeOut UserScript
// @namespace    https://github.com/s-vhs/AnimeOut-CommunityTools/tree/UserScript
// @version      1.0
// @description  Some minor tweaks for AnimeOut.
// @author       ForsakenMaiden
// @match        https://www.animeout.xyz/*
// @updateURL    https://github.com/s-vhs/AnimeOut-CommunityTools/raw/refs/heads/Userscript/animeout.user.js
// @downloadURL  https://github.com/s-vhs/AnimeOut-CommunityTools/raw/refs/heads/Userscript/animeout.user.js
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Function to extract FTP path from download links
    function getFTPPath(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        // Find the first "Direct Download" link
        const link = container.querySelector('a[href^="http://nimbus.animeout.com"]');
        if (!link) return null;

        const url = link.href;
        // Convert URL to FTP path
        // Remove http://
        let ftpPath = url.replace('http://', '');
        // Insert public_html after domain
        ftpPath = ftpPath.replace('/series/', '/public_html/series/');
        // Remove filename (everything after last /)
        ftpPath = ftpPath.substring(0, ftpPath.lastIndexOf('/'));
        // Decode URL-encoded characters (e.g., %20 to space)
        ftpPath = decodeURIComponent(ftpPath);

        return ftpPath;
    }

    // Function to copy text to clipboard
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            console.log('Copied to clipboard:', text);
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    // Create and add buttons
    function addButtons() {
        const pageTitle = document.querySelector('h1.page-title');
        if (!pageTitle) return;

        // Create container for buttons
        const buttonContainer = document.createElement('div');
        buttonContainer.style.marginTop = '10px';
        buttonContainer.style.marginBottom = '10px';

        // Create 1080p button
        const btn1080p = document.createElement('button');
        btn1080p.textContent = 'Copy 1080p FTP Path';
        btn1080p.style.marginRight = '10px';
        btn1080p.style.padding = '8px 15px';
        btn1080p.style.cursor = 'pointer';
        btn1080p.style.backgroundColor = '#4CAF50';
        btn1080p.style.color = 'white';
        btn1080p.style.border = 'none';
        btn1080p.style.borderRadius = '4px';
        btn1080p.style.fontSize = '14px';
        btn1080p.addEventListener('click', () => {
            const ftpPath = getFTPPath('1080pLinks');
            if (ftpPath) {
                copyToClipboard(ftpPath);
                btn1080p.textContent = 'Copied!';
                btn1080p.style.backgroundColor = '#45a049';
                setTimeout(() => {
                    btn1080p.textContent = 'Copy 1080p FTP Path';
                    btn1080p.style.backgroundColor = '#4CAF50';
                }, 2000);
            } else {
                alert('Could not find 1080p links');
            }
        });

        // Create 720p button
        const btn720p = document.createElement('button');
        btn720p.textContent = 'Copy 720p FTP Path';
        btn720p.style.padding = '8px 15px';
        btn720p.style.cursor = 'pointer';
        btn720p.style.backgroundColor = '#2196F3';
        btn720p.style.color = 'white';
        btn720p.style.border = 'none';
        btn720p.style.borderRadius = '4px';
        btn720p.style.fontSize = '14px';
        btn720p.addEventListener('click', () => {
            const ftpPath = getFTPPath('720pLinks');
            if (ftpPath) {
                copyToClipboard(ftpPath);
                btn720p.textContent = 'Copied!';
                btn720p.style.backgroundColor = '#0b7dda';
                setTimeout(() => {
                    btn720p.textContent = 'Copy 720p FTP Path';
                    btn720p.style.backgroundColor = '#2196F3';
                }, 2000);
            } else {
                alert('Could not find 720p links');
            }
        });

        buttonContainer.appendChild(btn1080p);
        buttonContainer.appendChild(btn720p);

        // Insert buttons after the page title
        pageTitle.parentNode.insertBefore(buttonContainer, pageTitle.nextSibling);
    }

    // Wait for page to load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addButtons);
    } else {
        addButtons();
    }
})();
