/**
 * Currency Metadata for NVC Banking Platform
 * Provides flag paths and country names for currencies
 */

const currencyMetadata = {
    // Native NVC currencies
    'NVCT': { flag: '/static/images/flags/globe.svg', name: 'NVC Token', country: 'NVC' },
    'SPU': { flag: '/static/images/flags/globe.svg', name: 'Special Purpose Unit', country: 'NVC' },
    'TU': { flag: '/static/images/flags/globe.svg', name: 'Treasury Unit', country: 'NVC' },
    'AFD1': { flag: '/static/images/flags/globe.svg', name: 'American Federation Dollar', country: 'AFD' },
    'SFN': { flag: '/static/images/flags/globe.svg', name: 'Swifin Coin', country: 'SFN' },
    'AKLUMI': { flag: '/static/images/flags/globe.svg', name: 'Ak Lumi', country: 'ECO-6' },
    
    // Major world currencies
    'USD': { flag: '/static/images/flags/us.svg', name: 'US Dollar', country: 'United States' },
    'EUR': { flag: '/static/images/flags/eu.svg', name: 'Euro', country: 'European Union' },
    'GBP': { flag: '/static/images/flags/gb.svg', name: 'British Pound', country: 'United Kingdom' },
    'JPY': { flag: '/static/images/flags/jp.svg', name: 'Japanese Yen', country: 'Japan' },
    'CHF': { flag: '/static/images/flags/ch.svg', name: 'Swiss Franc', country: 'Switzerland' },
    'CAD': { flag: '/static/images/flags/ca.svg', name: 'Canadian Dollar', country: 'Canada' },
    'AUD': { flag: '/static/images/flags/au.svg', name: 'Australian Dollar', country: 'Australia' },
    'NZD': { flag: '/static/images/flags/nz.svg', name: 'New Zealand Dollar', country: 'New Zealand' },
    'CNY': { flag: '/static/images/flags/cn.svg', name: 'Chinese Yuan Renminbi', country: 'China' },
    'HKD': { flag: '/static/images/flags/hk.svg', name: 'Hong Kong Dollar', country: 'Hong Kong' },
    'SGD': { flag: '/static/images/flags/sg.svg', name: 'Singapore Dollar', country: 'Singapore' },
    'INR': { flag: '/static/images/flags/in.svg', name: 'Indian Rupee', country: 'India' },
    'RUB': { flag: '/static/images/flags/ru.svg', name: 'Russian Ruble', country: 'Russia' },
    'BRL': { flag: '/static/images/flags/br.svg', name: 'Brazilian Real', country: 'Brazil' },
    'MXN': { flag: '/static/images/flags/mx.svg', name: 'Mexican Peso', country: 'Mexico' },
    'SEK': { flag: '/static/images/flags/se.svg', name: 'Swedish Krona', country: 'Sweden' },
    'NOK': { flag: '/static/images/flags/no.svg', name: 'Norwegian Krone', country: 'Norway' },
    'DKK': { flag: '/static/images/flags/dk.svg', name: 'Danish Krone', country: 'Denmark' },
    'PLN': { flag: '/static/images/flags/pl.svg', name: 'Polish Zloty', country: 'Poland' },
    'TRY': { flag: '/static/images/flags/tr.svg', name: 'Turkish Lira', country: 'Turkey' },
    
    // North African currencies
    'DZD': { flag: '/static/images/flags/dz.svg', name: 'Algerian Dinar', country: 'Algeria' },
    'EGP': { flag: '/static/images/flags/eg.svg', name: 'Egyptian Pound', country: 'Egypt' },
    'LYD': { flag: '/static/images/flags/ly.svg', name: 'Libyan Dinar', country: 'Libya' },
    'MAD': { flag: '/static/images/flags/ma.svg', name: 'Moroccan Dirham', country: 'Morocco' },
    'SDG': { flag: '/static/images/flags/sd.svg', name: 'Sudanese Pound', country: 'Sudan' },
    'TND': { flag: '/static/images/flags/tn.svg', name: 'Tunisian Dinar', country: 'Tunisia' },
    
    // West African currencies
    'NGN': { flag: '/static/images/flags/ng.svg', name: 'Nigerian Naira', country: 'Nigeria' },
    'GHS': { flag: '/static/images/flags/gh.svg', name: 'Ghanaian Cedi', country: 'Ghana' },
    'XOF': { flag: '/static/images/flags/sn.svg', name: 'CFA Franc BCEAO', country: 'BCEAO' },
    'GMD': { flag: '/static/images/flags/gm.svg', name: 'Gambian Dalasi', country: 'Gambia' },
    'GNF': { flag: '/static/images/flags/gn.svg', name: 'Guinean Franc', country: 'Guinea' },
    'LRD': { flag: '/static/images/flags/lr.svg', name: 'Liberian Dollar', country: 'Liberia' },
    'SLL': { flag: '/static/images/flags/sl.svg', name: 'Sierra Leonean Leone', country: 'Sierra Leone' },
    'SLE': { flag: '/static/images/flags/sl.svg', name: 'Sierra Leonean Leone (new)', country: 'Sierra Leone' },
    'CVE': { flag: '/static/images/flags/cv.svg', name: 'Cape Verdean Escudo', country: 'Cape Verde' },
    
    // Central African currencies
    'XAF': { flag: '/static/images/flags/cm.svg', name: 'CFA Franc BEAC', country: 'BEAC' },
    'CDF': { flag: '/static/images/flags/cd.svg', name: 'Congolese Franc', country: 'DR Congo' },
    'STN': { flag: '/static/images/flags/st.svg', name: 'São Tomé and Príncipe Dobra', country: 'São Tomé and Príncipe' },
    
    // East African currencies
    'KES': { flag: '/static/images/flags/ke.svg', name: 'Kenyan Shilling', country: 'Kenya' },
    'ETB': { flag: '/static/images/flags/et.svg', name: 'Ethiopian Birr', country: 'Ethiopia' },
    'UGX': { flag: '/static/images/flags/ug.svg', name: 'Ugandan Shilling', country: 'Uganda' },
    'TZS': { flag: '/static/images/flags/tz.svg', name: 'Tanzanian Shilling', country: 'Tanzania' },
    'RWF': { flag: '/static/images/flags/rw.svg', name: 'Rwandan Franc', country: 'Rwanda' },
    'BIF': { flag: '/static/images/flags/bi.svg', name: 'Burundian Franc', country: 'Burundi' },
    'DJF': { flag: '/static/images/flags/dj.svg', name: 'Djiboutian Franc', country: 'Djibouti' },
    'ERN': { flag: '/static/images/flags/er.svg', name: 'Eritrean Nakfa', country: 'Eritrea' },
    'SSP': { flag: '/static/images/flags/ss.svg', name: 'South Sudanese Pound', country: 'South Sudan' },
    'SOS': { flag: '/static/images/flags/so.svg', name: 'Somali Shilling', country: 'Somalia' },
    
    // Southern African currencies
    'ZAR': { flag: '/static/images/flags/za.svg', name: 'South African Rand', country: 'South Africa' },
    'LSL': { flag: '/static/images/flags/ls.svg', name: 'Lesotho Loti', country: 'Lesotho' },
    'NAD': { flag: '/static/images/flags/na.svg', name: 'Namibian Dollar', country: 'Namibia' },
    'SZL': { flag: '/static/images/flags/sz.svg', name: 'Swazi Lilangeni', country: 'Eswatini' },
    'BWP': { flag: '/static/images/flags/bw.svg', name: 'Botswana Pula', country: 'Botswana' },
    'ZMW': { flag: '/static/images/flags/zm.svg', name: 'Zambian Kwacha', country: 'Zambia' },
    'MWK': { flag: '/static/images/flags/mw.svg', name: 'Malawian Kwacha', country: 'Malawi' },
    'ZWL': { flag: '/static/images/flags/zw.svg', name: 'Zimbabwean Dollar', country: 'Zimbabwe' },
    'MZN': { flag: '/static/images/flags/mz.svg', name: 'Mozambican Metical', country: 'Mozambique' },
    'MGA': { flag: '/static/images/flags/mg.svg', name: 'Malagasy Ariary', country: 'Madagascar' },
    'SCR': { flag: '/static/images/flags/sc.svg', name: 'Seychellois Rupee', country: 'Seychelles' },
    'MUR': { flag: '/static/images/flags/mu.svg', name: 'Mauritian Rupee', country: 'Mauritius' },
    'AOA': { flag: '/static/images/flags/ao.svg', name: 'Angolan Kwanza', country: 'Angola' },
    
    // Cryptocurrencies
    'BTC': { flag: '/static/images/flags/crypto.svg', name: 'Bitcoin', country: 'Global' },
    'ETH': { flag: '/static/images/flags/crypto.svg', name: 'Ethereum', country: 'Global' },
    'USDT': { flag: '/static/images/flags/crypto.svg', name: 'Tether', country: 'Global' },
    'BNB': { flag: '/static/images/flags/crypto.svg', name: 'Binance Coin', country: 'Global' },
    'SOL': { flag: '/static/images/flags/crypto.svg', name: 'Solana', country: 'Global' },
    'XRP': { flag: '/static/images/flags/crypto.svg', name: 'XRP (Ripple)', country: 'Global' },
    'USDC': { flag: '/static/images/flags/crypto.svg', name: 'USD Coin', country: 'Global' },
    'ADA': { flag: '/static/images/flags/crypto.svg', name: 'Cardano', country: 'Global' },
    'AVAX': { flag: '/static/images/flags/crypto.svg', name: 'Avalanche', country: 'Global' },
    'DOGE': { flag: '/static/images/flags/crypto.svg', name: 'Dogecoin', country: 'Global' },
    'DOT': { flag: '/static/images/flags/crypto.svg', name: 'Polkadot', country: 'Global' },
    'MATIC': { flag: '/static/images/flags/crypto.svg', name: 'Polygon', country: 'Global' },
    'LTC': { flag: '/static/images/flags/crypto.svg', name: 'Litecoin', country: 'Global' },
    'SHIB': { flag: '/static/images/flags/crypto.svg', name: 'Shiba Inu', country: 'Global' },
    'DAI': { flag: '/static/images/flags/crypto.svg', name: 'Dai', country: 'Global' },
    'TRX': { flag: '/static/images/flags/crypto.svg', name: 'TRON', country: 'Global' },
    'UNI': { flag: '/static/images/flags/crypto.svg', name: 'Uniswap', country: 'Global' },
    'LINK': { flag: '/static/images/flags/crypto.svg', name: 'Chainlink', country: 'Global' },
    'ATOM': { flag: '/static/images/flags/crypto.svg', name: 'Cosmos', country: 'Global' },
    'XMR': { flag: '/static/images/flags/crypto.svg', name: 'Monero', country: 'Global' }
};

/**
 * Get metadata for a currency
 * @param {string} currencyCode - The currency code (e.g., 'USD', 'NVCT')
 * @returns {Object} Currency metadata or default object if not found
 */
function getCurrencyMetadata(currencyCode) {
    // Return the metadata if it exists, or a default object
    return currencyMetadata[currencyCode] || { 
        flag: '/static/images/flags/globe.svg', 
        name: currencyCode, 
        country: 'Global' 
    };
}

/**
 * Format a currency option with a flag
 * @param {string} currencyCode - The currency code (e.g., 'USD', 'NVCT')
 * @returns {string} HTML string with flag and currency code
 */
function formatCurrencyOption(currencyCode) {
    const metadata = getCurrencyMetadata(currencyCode);
    return `<img src="${metadata.flag}" alt="${metadata.country}" class="currency-flag" width="16" height="16"> ${currencyCode} - ${metadata.name}`;
}

/**
 * Initialize currency dropdowns with flags
 * @param {string} fromSelectId - ID of the "from currency" select element
 * @param {string} toSelectId - ID of the "to currency" select element
 */
function initCurrencyDropdowns(fromSelectId = 'from_currency', toSelectId = 'to_currency') {
    // Helper function to update select options
    function updateSelectOptions(selectId) {
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // For each option in the select
        Array.from(select.options).forEach(option => {
            const currencyCode = option.value;
            option.innerHTML = formatCurrencyOption(currencyCode);
        });
    }
    
    // Update both selects
    updateSelectOptions(fromSelectId);
    updateSelectOptions(toSelectId);
}