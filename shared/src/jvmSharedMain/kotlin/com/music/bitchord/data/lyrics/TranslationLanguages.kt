package com.music.bitchord.data.lyrics

import java.util.Locale

/** A target language Google Translate accepts. */
data class TranslationLanguage(val code: String, val fallbackName: String)

/**
 * Languages offered by the lyrics translation picker.
 *
 * Ordered to put the most common targets at the head, followed by the rest in
 * English alphabetical order. The list is long enough that the picker provides
 * a filter field.
 */
val TRANSLATION_LANGUAGES = listOf(
    // Common targets first
    TranslationLanguage("pt-BR", "Portuguese (Brazil)"),
    TranslationLanguage("pt-PT", "Portuguese (Portugal)"),
    TranslationLanguage("en", "English"),
    TranslationLanguage("es", "Spanish"),
    TranslationLanguage("fr", "French"),
    TranslationLanguage("de", "German"),
    TranslationLanguage("it", "Italian"),
    TranslationLanguage("ja", "Japanese"),
    TranslationLanguage("ko", "Korean"),
    TranslationLanguage("zh-CN", "Chinese (Simplified)"),
    TranslationLanguage("zh-TW", "Chinese (Traditional)"),
    TranslationLanguage("ru", "Russian"),
    TranslationLanguage("ar", "Arabic"),
    TranslationLanguage("hi", "Hindi"),
    TranslationLanguage("id", "Indonesian"),
    TranslationLanguage("tr", "Turkish"),
    TranslationLanguage("vi", "Vietnamese"),
    TranslationLanguage("th", "Thai"),
    TranslationLanguage("pl", "Polish"),
    TranslationLanguage("nl", "Dutch"),
    // Alphabetical
    TranslationLanguage("af", "Afrikaans"),
    TranslationLanguage("sq", "Albanian"),
    TranslationLanguage("am", "Amharic"),
    TranslationLanguage("hy", "Armenian"),
    TranslationLanguage("as", "Assamese"),
    TranslationLanguage("ay", "Aymara"),
    TranslationLanguage("az", "Azerbaijani"),
    TranslationLanguage("bm", "Bambara"),
    TranslationLanguage("eu", "Basque"),
    TranslationLanguage("be", "Belarusian"),
    TranslationLanguage("bn", "Bengali"),
    TranslationLanguage("bho", "Bhojpuri"),
    TranslationLanguage("bs", "Bosnian"),
    TranslationLanguage("bg", "Bulgarian"),
    TranslationLanguage("ca", "Catalan"),
    TranslationLanguage("ceb", "Cebuano"),
    TranslationLanguage("co", "Corsican"),
    TranslationLanguage("hr", "Croatian"),
    TranslationLanguage("cs", "Czech"),
    TranslationLanguage("da", "Danish"),
    TranslationLanguage("dv", "Dhivehi"),
    TranslationLanguage("doi", "Dogri"),
    TranslationLanguage("eo", "Esperanto"),
    TranslationLanguage("et", "Estonian"),
    TranslationLanguage("ee", "Ewe"),
    TranslationLanguage("fil", "Filipino (Tagalog)"),
    TranslationLanguage("fi", "Finnish"),
    TranslationLanguage("fy", "Frisian"),
    TranslationLanguage("gl", "Galician"),
    TranslationLanguage("ka", "Georgian"),
    TranslationLanguage("el", "Greek"),
    TranslationLanguage("gn", "Guarani"),
    TranslationLanguage("gu", "Gujarati"),
    TranslationLanguage("ht", "Haitian Creole"),
    TranslationLanguage("ha", "Hausa"),
    TranslationLanguage("haw", "Hawaiian"),
    TranslationLanguage("he", "Hebrew"),
    TranslationLanguage("hmn", "Hmong"),
    TranslationLanguage("hu", "Hungarian"),
    TranslationLanguage("is", "Icelandic"),
    TranslationLanguage("ig", "Igbo"),
    TranslationLanguage("ilo", "Ilocano"),
    TranslationLanguage("ga", "Irish"),
    TranslationLanguage("jv", "Javanese"),
    TranslationLanguage("kn", "Kannada"),
    TranslationLanguage("kk", "Kazakh"),
    TranslationLanguage("km", "Khmer"),
    TranslationLanguage("rw", "Kinyarwanda"),
    TranslationLanguage("gom", "Konkani"),
    TranslationLanguage("kri", "Krio"),
    TranslationLanguage("ku", "Kurdish (Kurmanji)"),
    TranslationLanguage("ckb", "Kurdish (Sorani)"),
    TranslationLanguage("ky", "Kyrgyz"),
    TranslationLanguage("lo", "Lao"),
    TranslationLanguage("la", "Latin"),
    TranslationLanguage("lv", "Latvian"),
    TranslationLanguage("ln", "Lingala"),
    TranslationLanguage("lt", "Lithuanian"),
    TranslationLanguage("lg", "Luganda"),
    TranslationLanguage("lb", "Luxembourgish"),
    TranslationLanguage("mk", "Macedonian"),
    TranslationLanguage("mai", "Maithili"),
    TranslationLanguage("mg", "Malagasy"),
    TranslationLanguage("ms", "Malay"),
    TranslationLanguage("ml", "Malayalam"),
    TranslationLanguage("mt", "Maltese"),
    TranslationLanguage("mi", "Maori"),
    TranslationLanguage("mr", "Marathi"),
    TranslationLanguage("mni-Mtei", "Meiteilon (Manipuri)"),
    TranslationLanguage("lus", "Mizo"),
    TranslationLanguage("mn", "Mongolian"),
    TranslationLanguage("my", "Myanmar (Burmese)"),
    TranslationLanguage("ne", "Nepali"),
    TranslationLanguage("nso", "Northern Sotho"),
    TranslationLanguage("no", "Norwegian"),
    TranslationLanguage("ny", "Nyanja (Chichewa)"),
    TranslationLanguage("or", "Odia (Oriya)"),
    TranslationLanguage("om", "Oromo"),
    TranslationLanguage("ps", "Pashto"),
    TranslationLanguage("fa", "Persian"),
    TranslationLanguage("pa", "Punjabi"),
    TranslationLanguage("qu", "Quechua"),
    TranslationLanguage("ro", "Romanian"),
    TranslationLanguage("sm", "Samoan"),
    TranslationLanguage("sa", "Sanskrit"),
    TranslationLanguage("gd", "Scots Gaelic"),
    TranslationLanguage("sr", "Serbian"),
    TranslationLanguage("st", "Sesotho"),
    TranslationLanguage("sn", "Shona"),
    TranslationLanguage("sd", "Sindhi"),
    TranslationLanguage("si", "Sinhala"),
    TranslationLanguage("sk", "Slovak"),
    TranslationLanguage("sl", "Slovenian"),
    TranslationLanguage("so", "Somali"),
    TranslationLanguage("su", "Sundanese"),
    TranslationLanguage("sw", "Swahili"),
    TranslationLanguage("sv", "Swedish"),
    TranslationLanguage("tg", "Tajik"),
    TranslationLanguage("ta", "Tamil"),
    TranslationLanguage("tt", "Tatar"),
    TranslationLanguage("te", "Telugu"),
    TranslationLanguage("ti", "Tigrinya"),
    TranslationLanguage("ts", "Tsonga"),
    TranslationLanguage("tk", "Turkmen"),
    TranslationLanguage("ak", "Twi (Akan)"),
    TranslationLanguage("uk", "Ukrainian"),
    TranslationLanguage("ur", "Urdu"),
    TranslationLanguage("ug", "Uyghur"),
    TranslationLanguage("uz", "Uzbek"),
    TranslationLanguage("cy", "Welsh"),
    TranslationLanguage("xh", "Xhosa"),
    TranslationLanguage("yi", "Yiddish"),
    TranslationLanguage("yo", "Yoruba"),
    TranslationLanguage("zu", "Zulu"),
)

/**
 * Display name for [code] in [inLocale], falling back to its English entry
 * in [TRANSLATION_LANGUAGES] and then to the raw code.
 */
fun translationLanguageName(code: String, inLocale: Locale): String {
    if (code.equals("pt-BR", ignoreCase = true)) return "Português (Brasil)"
    if (code.equals("pt-PT", ignoreCase = true) || code.equals("pt", ignoreCase = true)) return "Português (Portugal)"
    val tag = code.replace('_', '-')
    val native = Locale.forLanguageTag(tag).getDisplayName(inLocale)
        .replaceFirstChar { if (it.isLowerCase()) it.titlecase(inLocale) else it.toString() }
    if (native.isNotBlank() && !native.equals(tag, ignoreCase = true)) return native
    return TRANSLATION_LANGUAGES.firstOrNull { it.code.equals(code, ignoreCase = true) }
        ?.fallbackName
        ?: code
}
