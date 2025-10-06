import { writable } from 'svelte/store';

export function localStorageStore(key, initialValue) {
    let storedValue;

    try {
        const json = localStorage.getItem(key);
        storedValue = json ? JSON.parse(json) : initialValue;
    } catch (e) {
        console.error('Error reading from localStorage', e);
        storedValue = initialValue;
    }

    const store = writable(storedValue);

    store.subscribe(value => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Error writing to localStorage', e);
        }
    });

    return store;
}
