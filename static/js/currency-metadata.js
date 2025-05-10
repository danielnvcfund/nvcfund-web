/**
 * Currency Metadata for NVC Banking Platform
 * Provides mapping of currency codes to country information and symbols
 */

// Currency metadata including country codes (for flag display) and symbols
const CURRENCY_METADATA = {
    // Native Platform Currencies
    "NVCT": { countryCode: "globe", symbol: "₦", name: "NVC Token" },
    "SPU": { countryCode: "globe", symbol: "SPU", name: "Special Purpose Unit" },
    "TU": { countryCode: "globe", symbol: "TU", name: "Treasury Unit" },
    "AFD1": { countryCode: "globe", symbol: "AFD", name: "American Federation Dollar" },
    "SFN": { countryCode: "globe", symbol: "SFN", name: "SFN Coin (Swifin)" },
    "AKLUMI": { countryCode: "globe", symbol: "AKL", name: "Ak Lumi (Eco-6)" },
    
    // Major World Currencies
    "USD": { countryCode: "us", symbol: "$", name: "US Dollar" },
    "EUR": { countryCode: "eu", symbol: "€", name: "Euro" },
    "GBP": { countryCode: "gb", symbol: "£", name: "British Pound" },
    "JPY": { countryCode: "jp", symbol: "¥", name: "Japanese Yen" },
    "CHF": { countryCode: "ch", symbol: "CHF", name: "Swiss Franc" },
    "CAD": { countryCode: "ca", symbol: "C$", name: "Canadian Dollar" },
    "AUD": { countryCode: "au", symbol: "A$", name: "Australian Dollar" },
    "NZD": { countryCode: "nz", symbol: "NZ$", name: "New Zealand Dollar" },
    "CNY": { countryCode: "cn", symbol: "¥", name: "Chinese Yuan" },
    "HKD": { countryCode: "hk", symbol: "HK$", name: "Hong Kong Dollar" },
    "SGD": { countryCode: "sg", symbol: "S$", name: "Singapore Dollar" },
    "INR": { countryCode: "in", symbol: "₹", name: "Indian Rupee" },
    "RUB": { countryCode: "ru", symbol: "₽", name: "Russian Ruble" },
    "BRL": { countryCode: "br", symbol: "R$", name: "Brazilian Real" },
    "MXN": { countryCode: "mx", symbol: "$", name: "Mexican Peso" },
    "SEK": { countryCode: "se", symbol: "kr", name: "Swedish Krona" },
    "NOK": { countryCode: "no", symbol: "kr", name: "Norwegian Krone" },
    "DKK": { countryCode: "dk", symbol: "kr", name: "Danish Krone" },
    "PLN": { countryCode: "pl", symbol: "zł", name: "Polish Zloty" },
    "TRY": { countryCode: "tr", symbol: "₺", name: "Turkish Lira" },
    
    // North African Currencies
    "DZD": { countryCode: "dz", symbol: "د.ج", name: "Algerian Dinar" },
    "EGP": { countryCode: "eg", symbol: "£", name: "Egyptian Pound" },
    "LYD": { countryCode: "ly", symbol: "ل.د", name: "Libyan Dinar" },
    "MAD": { countryCode: "ma", symbol: "د.م.", name: "Moroccan Dirham" },
    "SDG": { countryCode: "sd", symbol: "ج.س.", name: "Sudanese Pound" },
    "TND": { countryCode: "tn", symbol: "د.ت", name: "Tunisian Dinar" },
    
    // West African Currencies
    "NGN": { countryCode: "ng", symbol: "₦", name: "Nigerian Naira" },
    "GHS": { countryCode: "gh", symbol: "₵", name: "Ghanaian Cedi" },
    "XOF": { countryCode: "senegal", symbol: "CFA", name: "CFA Franc BCEAO" },
    "GMD": { countryCode: "gm", symbol: "D", name: "Gambian Dalasi" },
    "GNF": { countryCode: "gn", symbol: "FG", name: "Guinean Franc" },
    "LRD": { countryCode: "lr", symbol: "L$", name: "Liberian Dollar" },
    "SLL": { countryCode: "sl", symbol: "Le", name: "Sierra Leonean Leone (old)" },
    "SLE": { countryCode: "sl", symbol: "Le", name: "Sierra Leonean Leone" },
    "CVE": { countryCode: "cv", symbol: "$", name: "Cape Verdean Escudo" },
    
    // Central African Currencies
    "XAF": { countryCode: "cm", symbol: "FCFA", name: "CFA Franc BEAC" },
    "CDF": { countryCode: "cd", symbol: "FC", name: "Congolese Franc" },
    "STN": { countryCode: "st", symbol: "Db", name: "São Tomé and Príncipe Dobra" },
    
    // East African Currencies
    "KES": { countryCode: "ke", symbol: "KSh", name: "Kenyan Shilling" },
    "ETB": { countryCode: "et", symbol: "Br", name: "Ethiopian Birr" },
    "UGX": { countryCode: "ug", symbol: "USh", name: "Ugandan Shilling" },
    "TZS": { countryCode: "tz", symbol: "TSh", name: "Tanzanian Shilling" },
    "RWF": { countryCode: "rw", symbol: "R₣", name: "Rwandan Franc" },
    "BIF": { countryCode: "bi", symbol: "FBu", name: "Burundian Franc" },
    "DJF": { countryCode: "dj", symbol: "Fdj", name: "Djiboutian Franc" },
    "ERN": { countryCode: "er", symbol: "Nfk", name: "Eritrean Nakfa" },
    "SSP": { countryCode: "ss", symbol: "£", name: "South Sudanese Pound" },
    "SOS": { countryCode: "so", symbol: "Sh", name: "Somali Shilling" },
    
    // Southern African Currencies
    "ZAR": { countryCode: "za", symbol: "R", name: "South African Rand" },
    "LSL": { countryCode: "ls", symbol: "L", name: "Lesotho Loti" },
    "NAD": { countryCode: "na", symbol: "N$", name: "Namibian Dollar" },
    "SZL": { countryCode: "sz", symbol: "E", name: "Swazi Lilangeni" },
    "BWP": { countryCode: "bw", symbol: "P", name: "Botswana Pula" },
    "ZMW": { countryCode: "zm", symbol: "ZK", name: "Zambian Kwacha" },
    "MWK": { countryCode: "mw", symbol: "MK", name: "Malawian Kwacha" },
    "ZWL": { countryCode: "zw", symbol: "$", name: "Zimbabwean Dollar" },
    "MZN": { countryCode: "mz", symbol: "MT", name: "Mozambican Metical" },
    "MGA": { countryCode: "mg", symbol: "Ar", name: "Malagasy Ariary" },
    "SCR": { countryCode: "sc", symbol: "SR", name: "Seychellois Rupee" },
    "MUR": { countryCode: "mu", symbol: "₨", name: "Mauritian Rupee" },
    "AOA": { countryCode: "ao", symbol: "Kz", name: "Angolan Kwanza" },
    
    // Asian Currencies
    "IDR": { countryCode: "id", symbol: "Rp", name: "Indonesian Rupiah" },
    "MYR": { countryCode: "my", symbol: "RM", name: "Malaysian Ringgit" },
    "PHP": { countryCode: "ph", symbol: "₱", name: "Philippine Peso" },
    "THB": { countryCode: "th", symbol: "฿", name: "Thai Baht" },
    "VND": { countryCode: "vn", symbol: "₫", name: "Vietnamese Dong" },
    "KRW": { countryCode: "kr", symbol: "₩", name: "South Korean Won" },
    "TWD": { countryCode: "tw", symbol: "NT$", name: "Taiwan New Dollar" },
    "PKR": { countryCode: "pk", symbol: "₨", name: "Pakistani Rupee" },
    "BDT": { countryCode: "bd", symbol: "৳", name: "Bangladeshi Taka" },
    "NPR": { countryCode: "np", symbol: "₨", name: "Nepalese Rupee" },
    "LKR": { countryCode: "lk", symbol: "₨", name: "Sri Lankan Rupee" },
    
    // Middle Eastern Currencies
    "AED": { countryCode: "ae", symbol: "د.إ", name: "UAE Dirham" },
    "SAR": { countryCode: "sa", symbol: "ر.س", name: "Saudi Riyal" },
    "QAR": { countryCode: "qa", symbol: "ر.ق", name: "Qatari Riyal" },
    "OMR": { countryCode: "om", symbol: "ر.ع.", name: "Omani Rial" },
    "BHD": { countryCode: "bh", symbol: "د.ب", name: "Bahraini Dinar" },
    "KWD": { countryCode: "kw", symbol: "د.ك", name: "Kuwaiti Dinar" },
    "ILS": { countryCode: "il", symbol: "₪", name: "Israeli New Shekel" },
    "JOD": { countryCode: "jo", symbol: "د.ا", name: "Jordanian Dinar" },
    "LBP": { countryCode: "lb", symbol: "ل.ل", name: "Lebanese Pound" },
    "IRR": { countryCode: "ir", symbol: "﷼", name: "Iranian Rial" },
    "IQD": { countryCode: "iq", symbol: "ع.د", name: "Iraqi Dinar" },
    
    // Latin American Currencies
    "ARS": { countryCode: "ar", symbol: "$", name: "Argentine Peso" },
    "CLP": { countryCode: "cl", symbol: "$", name: "Chilean Peso" },
    "COP": { countryCode: "co", symbol: "$", name: "Colombian Peso" },
    "PEN": { countryCode: "pe", symbol: "S/", name: "Peruvian Sol" },
    "UYU": { countryCode: "uy", symbol: "$U", name: "Uruguayan Peso" },
    "VES": { countryCode: "ve", symbol: "Bs.S", name: "Venezuelan Bolivar" },
    "BOB": { countryCode: "bo", symbol: "Bs", name: "Bolivian Boliviano" },
    "PYG": { countryCode: "py", symbol: "₲", name: "Paraguayan Guarani" },
    "DOP": { countryCode: "do", symbol: "RD$", name: "Dominican Peso" },
    "CRC": { countryCode: "cr", symbol: "₡", name: "Costa Rican Colon" },
    "JMD": { countryCode: "jm", symbol: "J$", name: "Jamaican Dollar" },
    "TTD": { countryCode: "tt", symbol: "TT$", name: "Trinidad and Tobago Dollar" },
    
    // European Currencies (non-Euro)
    "CZK": { countryCode: "cz", symbol: "Kč", name: "Czech Koruna" },
    "HUF": { countryCode: "hu", symbol: "Ft", name: "Hungarian Forint" },
    "RON": { countryCode: "ro", symbol: "lei", name: "Romanian Leu" },
    "BGN": { countryCode: "bg", symbol: "лв", name: "Bulgarian Lev" },
    "HRK": { countryCode: "hr", symbol: "kn", name: "Croatian Kuna" },
    "RSD": { countryCode: "rs", symbol: "дин.", name: "Serbian Dinar" },
    "UAH": { countryCode: "ua", symbol: "₴", name: "Ukrainian Hryvnia" },
    "BYN": { countryCode: "by", symbol: "Br", name: "Belarusian Ruble" },
    
    // Cryptocurrencies 
    "BTC": { countryCode: "crypto", symbol: "₿", name: "Bitcoin" },
    "ETH": { countryCode: "crypto", symbol: "Ξ", name: "Ethereum" },
    "USDT": { countryCode: "crypto", symbol: "₮", name: "Tether" },
    "BNB": { countryCode: "crypto", symbol: "BNB", name: "Binance Coin" },
    "SOL": { countryCode: "crypto", symbol: "◎", name: "Solana" },
    "XRP": { countryCode: "crypto", symbol: "XRP", name: "XRP (Ripple)" },
    "USDC": { countryCode: "crypto", symbol: "USDC", name: "USD Coin" },
    "ADA": { countryCode: "crypto", symbol: "₳", name: "Cardano" },
    "AVAX": { countryCode: "crypto", symbol: "AVAX", name: "Avalanche" },
    "DOGE": { countryCode: "crypto", symbol: "Ð", name: "Dogecoin" },
    "DOT": { countryCode: "crypto", symbol: "DOT", name: "Polkadot" },
    "MATIC": { countryCode: "crypto", symbol: "MATIC", name: "Polygon" },
    "LTC": { countryCode: "crypto", symbol: "Ł", name: "Litecoin" },
    "SHIB": { countryCode: "crypto", symbol: "SHIB", name: "Shiba Inu" },
    "DAI": { countryCode: "crypto", symbol: "DAI", name: "Dai" },
    "TRX": { countryCode: "crypto", symbol: "TRX", name: "TRON" },
    "UNI": { countryCode: "crypto", symbol: "UNI", name: "Uniswap" },
    "LINK": { countryCode: "crypto", symbol: "LINK", name: "Chainlink" },
    "ATOM": { countryCode: "crypto", symbol: "ATOM", name: "Cosmos" },
    "XMR": { countryCode: "crypto", symbol: "ɱ", name: "Monero" },
    "ETC": { countryCode: "crypto", symbol: "ETC", name: "Ethereum Classic" },
    "FIL": { countryCode: "crypto", symbol: "FIL", name: "Filecoin" },
    "XLM": { countryCode: "crypto", symbol: "XLM", name: "Stellar" },
    "NEAR": { countryCode: "crypto", symbol: "NEAR", name: "NEAR Protocol" },
    "ALGO": { countryCode: "crypto", symbol: "ALGO", name: "Algorand" },
    "ZCASH": { countryCode: "crypto", symbol: "ⓩ", name: "Zcash" },
    "APE": { countryCode: "crypto", symbol: "APE", name: "ApeCoin" },
    "ICP": { countryCode: "crypto", symbol: "ICP", name: "Internet Computer" },
    "FLOW": { countryCode: "crypto", symbol: "FLOW", name: "Flow" },
    "VET": { countryCode: "crypto", symbol: "VET", name: "VeChain" }
};

/**
 * Get currency metadata for a given currency code
 * @param {string} currencyCode - The currency code (e.g., "USD", "NVCT")
 * @returns {object|null} Currency metadata or null if not found
 */
function getCurrencyMetadata(currencyCode) {
    return CURRENCY_METADATA[currencyCode] || null;
}

/**
 * Get flag URL for a given currency code
 * @param {string} currencyCode - The currency code (e.g., "USD", "NVCT") 
 * @returns {string} URL to the flag image
 */
function getCurrencyFlagUrl(currencyCode) {
    const metadata = getCurrencyMetadata(currencyCode);
    if (!metadata) {
        return '/static/images/flags/globe.svg'; // Default flag for unknown currencies
    }
    
    // Special handling for certain country codes
    switch (metadata.countryCode) {
        case 'globe':
            return '/static/images/flags/globe.svg';
        case 'crypto':
            return '/static/images/flags/crypto.svg';
        case 'eu':
            return '/static/images/flags/eu.svg';
        case 'senegal': // Representative country for XOF
            return '/static/images/flags/sn.svg';
        case 'cm': // Representative country for XAF
            return '/static/images/flags/cm.svg';
        default:
            return `/static/images/flags/${metadata.countryCode}.svg`;
    }
}

/**
 * Get formatted currency with flag and symbol
 * @param {string} currencyCode - The currency code (e.g., "USD", "NVCT")
 * @returns {object} Object with flag URL, symbol, and name
 */
function getFormattedCurrency(currencyCode) {
    const metadata = getCurrencyMetadata(currencyCode) || { 
        countryCode: 'globe', 
        symbol: currencyCode, 
        name: currencyCode 
    };
    
    return {
        flagUrl: getCurrencyFlagUrl(currencyCode),
        symbol: metadata.symbol,
        name: metadata.name
    };
}