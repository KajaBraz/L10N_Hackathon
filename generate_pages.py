import json
import os


def render_page(locale_json_path, output_html_path, lang_code):
    # 1. Load localized text resource file
    with open(locale_json_path, 'r', encoding='utf-8') as lf:
        data = json.load(lf)

    # 2. Load the decoupled HTML/CSS structure file
    template_path = os.path.join('templates', 'index_template.html')
    with open(template_path, 'r', encoding='utf-8') as tf:
        html_content = tf.read()

    # 3. Handle Currency Formatting
    currency_template = data['meta']['currency_format']

    # 4. Perform direct string replacements (100% immune to CSS brace errors)
    replacements = {
        "{{LANG_CODE}}": lang_code,
        "{{META_TITLE}}": data['meta']['title'],
        "{{META_SUBTITLE}}": data['meta']['subtitle'],
        "{{PROMO_LABEL}}": data['meta']['promo_label'],
        "{{PROMO_DATE}}": data['meta']['promo_date'],

        "{{PALIO_TITLE}}": data['sections']['palio']['title'],
        "{{PALIO_DESC}}": data['sections']['palio']['description'],
        "{{PALIO_ALT}}": data['sections']['palio']['img_alt'],
        "{{PALIO_PRICE}}": currency_template.format(price=data['sections']['palio']['price_value']),

        "{{CALCIO_TITLE}}": data['sections']['calcio']['title'],
        "{{CALCIO_DESC}}": data['sections']['calcio']['description'],
        "{{CALCIO_ALT}}": data['sections']['calcio']['img_alt'],
        "{{CALCIO_PRICE}}": currency_template.format(price=data['sections']['calcio']['price_value']),

        "{{NATURA_TITLE}}": data['sections']['natura']['title'],
        "{{NATURA_DESC}}": data['sections']['natura']['description'],
        "{{NATURA_ALT}}": data['sections']['natura']['img_alt'],
        "{{NATURA_PRICE}}": currency_template.format(price=data['sections']['natura']['price_value']),

        "{{FILM_TITLE}}": data['sections']['film']['title'],
        "{{FILM_DESC}}": data['sections']['film']['description'],
        "{{FILM_ALT}}": data['sections']['film']['img_alt'],
        "{{FILM_PRICE}}": currency_template.format(price=data['sections']['film']['price_value']),

        "{{FESTE_TITLE}}": data['sections']['feste']['title'],
        "{{FESTE_DESC}}": data['sections']['feste']['description'],
        "{{FESTE_ALT}}": data['sections']['feste']['img_alt'],
        "{{FESTE_PRICE}}": currency_template.format(price=data['sections']['feste']['price_value']),

        "{{ESPERIENZE_TITLE}}": data['sections']['esperienze']['title'],
        "{{ESPERIENZE_DESC}}": data['sections']['esperienze']['description'],
        "{{ESPERIENZE_ALT}}": data['sections']['esperienze']['img_alt'],
        "{{ESPERIENZE_PRICE}}": currency_template.format(price=data['sections']['esperienze']['price_value']),

        "{{MACCHINE_TITLE}}": data['sections']['macchine']['title'],
        "{{MACCHINE_DESC}}": data['sections']['macchine']['description'],
        "{{MACCHINE_ALT}}": data['sections']['macchine']['img_alt'],
        "{{MACCHINE_PRICE}}": currency_template.format(price=data['sections']['macchine']['price_value']),

        "{{MUSICA_TITLE}}": data['sections']['musica']['title'],
        "{{MUSICA_DESC}}": data['sections']['musica']['description'],
        "{{MUSICA_ALT}}": data['sections']['musica']['img_alt'],
        "{{MUSICA_PRICE}}": currency_template.format(price=data['sections']['musica']['price_value'])
    }

    # Apply all values to the code skeleton
    for key, val in replacements.items():
        html_content = html_content.replace(key, val)

    # 5. Save output file
    with open(output_html_path, 'w', encoding='utf-8') as outf:
        outf.write(html_content)

    print(f"Successfully generated: {output_html_path}")


if __name__ == '__main__':
    # Compile both language test instances safely
    render_page(os.path.join('locales', 'it.json'), 'index_it.html', 'it')
    render_page(os.path.join('locales', 'en.json'), 'index_en.html', 'en-US')