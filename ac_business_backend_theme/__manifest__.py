# -*- coding: utf-8 -*-
{
    'name': 'AC Business Backend Theme',
    'version': '15.0.1.0.0',
    'summary': 'Royal blue & white business backend theme for accounting software',
    'description': """
        A professional accounting-oriented backend theme.
        Features:
        - Royal blue and white colour palette suited to finance tools
        - Full-screen app drawer with clean business styling
        - Fixed left app sidebar with responsive widths
        - Responsive layouts from mobile phones to large LED displays
        - System typography for fast first paint (no CDN font wait)
    """,
    'author': 'Aswin Associate',
    'category': 'Theme/Backend',
    'depends': [
        'web',
        'base_setup',
        'web_editor',
        'mail',
    ],
    'data': [
        'data/webclient_templates.xml',
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'ac_business_backend_theme/static/src/colors.scss',
        ],
        'web._assets_backend_helpers': [
            'ac_business_backend_theme/static/src/variables.scss',
            'ac_business_backend_theme/static/src/mixins.scss',
        ],
        'web.assets_qweb': [
            'ac_business_backend_theme/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'ac_business_backend_theme/static/src/webclient/title_service.js',
            'ac_business_backend_theme/static/src/global.scss',
            'ac_business_backend_theme/static/src/webclient/**/*.scss',
            'ac_business_backend_theme/static/src/webclient/**/*.js',
            'ac_business_backend_theme/static/src/search/**/*.scss',
            'ac_business_backend_theme/static/src/legacy/**/*.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
