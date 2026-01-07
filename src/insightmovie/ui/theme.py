"""
InsightMovie Theme
Insightシリーズ統一デザインシステム
"""

# カラーパレット（InsightSlideと統一）
COLOR_PALETTE = {
    # 背景色
    "bg_primary": "#FFFFFF",           # メイン背景
    "bg_secondary": "#F8FAFC",         # セカンダリ背景（カード内）
    "bg_elevated": "#F1F5F9",          # 強調背景（ホバー等）
    "bg_sidebar": "#FAFBFC",           # サイドバー背景
    "bg_card": "#FFFFFF",              # カード背景
    "bg_input": "#FFFFFF",             # 入力フィールド背景

    # テキスト色（4段階の階層）
    "text_primary": "#1E293B",         # メインテキスト（見出し）
    "text_secondary": "#64748B",       # 本文テキスト
    "text_tertiary": "#6B7280",        # 補助テキスト
    "text_muted": "#94A3B8",           # 薄いテキスト（注釈）
    "text_placeholder": "#D1D5DB",     # プレースホルダー

    # ブランドカラー（落ち着いたブルー系）
    "brand_primary": "#3B82F6",        # プライマリブルー
    "brand_hover": "#2563EB",          # ホバー時（濃い）
    "brand_light": "#DBEAFE",          # 薄いブルー（選択背景）
    "brand_muted": "#93C5FD",          # ミュートブルー

    # セカンダリアクション
    "secondary_default": "#F3F4F6",    # セカンダリボタン背景
    "secondary_hover": "#E5E7EB",      # セカンダリホバー
    "secondary_border": "#D1D5DB",     # セカンダリボーダー

    # 機能別カラー
    "action_update": "#059669",        # 更新（グリーン）
    "action_compare": "#7C3AED",       # 比較（パープル）
    "action_danger": "#DC2626",        # 危険（赤・控えめ）

    # ステータス
    "success": "#10B981",              # 成功
    "success_light": "#D1FAE5",        # 成功（薄い）
    "warning": "#F59E0B",              # 警告
    "warning_light": "#FEF3C7",        # 警告（薄い）
    "error": "#EF4444",                # エラー
    "error_light": "#FEE2E2",          # エラー（薄い）
    "info": "#3B82F6",                 # 情報
    "info_light": "#DBEAFE",           # 情報（薄い）

    # ボーダー・区切り
    "border_light": "#E5E7EB",         # 薄いボーダー
    "border_default": "#E2E8F0",       # 標準ボーダー
    "border_dark": "#9CA3AF",          # 濃いボーダー
    "divider": "#F3F4F6",              # セクション区切り
}

# スペーシング
SPACING = {
    "none": 0,
    "xs": 4,
    "sm": 8,      # 基本単位
    "md": 12,
    "lg": 16,
    "xl": 24,
    "2xl": 32,
    "3xl": 48,
}

# 角丸
RADIUS = {
    "none": 0,
    "sm": 4,
    "default": 6,
    "md": 8,
    "lg": 12,
    "full": 9999,
}

# フォント（Windows環境）
FONT_FAMILY = "Segoe UI, Meiryo UI, sans-serif"


def get_stylesheet() -> str:
    """
    統一QStyleSheetを取得

    Returns:
        QStyleSheet文字列
    """
    return f"""
    /* ============================================
       InsightMovie Unified Theme
       Notion/Linear風モダンB2B SaaSデザイン
       ============================================ */

    /* メインウィンドウ */
    QMainWindow {{
        background-color: {COLOR_PALETTE['bg_primary']};
    }}

    /* 中央ウィジェット */
    QWidget {{
        background-color: {COLOR_PALETTE['bg_primary']};
        color: {COLOR_PALETTE['text_secondary']};
        font-family: {FONT_FAMILY};
        font-size: 11pt;
    }}

    /* グループボックス */
    QGroupBox {{
        background-color: {COLOR_PALETTE['bg_card']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['md']}px;
        margin-top: {SPACING['lg']}px;
        padding: {SPACING['lg']}px;
        font-weight: 600;
        color: {COLOR_PALETTE['text_primary']};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: {SPACING['md']}px;
        padding: 0 {SPACING['sm']}px;
        background-color: {COLOR_PALETTE['bg_card']};
        color: {COLOR_PALETTE['text_primary']};
        font-size: 12pt;
        font-weight: 600;
    }}

    /* ラベル */
    QLabel {{
        color: {COLOR_PALETTE['text_secondary']};
        background-color: transparent;
        border: none;
        padding: {SPACING['xs']}px 0;
    }}

    /* プライマリボタン */
    QPushButton {{
        background-color: {COLOR_PALETTE['brand_primary']};
        color: white;
        border: none;
        border-radius: {RADIUS['default']}px;
        padding: {SPACING['sm']}px {SPACING['lg']}px;
        font-weight: 600;
        font-size: 11pt;
        min-height: 32px;
    }}

    QPushButton:hover {{
        background-color: {COLOR_PALETTE['brand_hover']};
    }}

    QPushButton:pressed {{
        background-color: {COLOR_PALETTE['brand_hover']};
        padding-top: {SPACING['sm'] + 1}px;
    }}

    QPushButton:disabled {{
        background-color: {COLOR_PALETTE['secondary_default']};
        color: {COLOR_PALETTE['text_muted']};
    }}

    /* セカンダリボタン（objectName: secondaryButton） */
    QPushButton[class="secondary"] {{
        background-color: {COLOR_PALETTE['secondary_default']};
        color: {COLOR_PALETTE['text_secondary']};
        border: 1px solid {COLOR_PALETTE['secondary_border']};
    }}

    QPushButton[class="secondary"]:hover {{
        background-color: {COLOR_PALETTE['secondary_hover']};
    }}

    /* 成功ボタン */
    QPushButton[class="success"] {{
        background-color: {COLOR_PALETTE['action_update']};
        color: white;
    }}

    QPushButton[class="success"]:hover {{
        background-color: #047857;
    }}

    /* 危険ボタン */
    QPushButton[class="danger"] {{
        background-color: {COLOR_PALETTE['action_danger']};
        color: white;
    }}

    QPushButton[class="danger"]:hover {{
        background-color: #B91C1C;
    }}

    /* 小さいボタン */
    QPushButton[class="small"] {{
        padding: {SPACING['xs']}px {SPACING['md']}px;
        font-size: 10pt;
        min-height: 24px;
    }}

    /* テキストエディット */
    QTextEdit, QPlainTextEdit {{
        background-color: {COLOR_PALETTE['bg_input']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['default']}px;
        padding: {SPACING['sm']}px;
        color: {COLOR_PALETTE['text_primary']};
        selection-background-color: {COLOR_PALETTE['brand_light']};
    }}

    QTextEdit:focus, QPlainTextEdit:focus {{
        border: 2px solid {COLOR_PALETTE['brand_primary']};
        padding: {SPACING['sm'] - 1}px;
    }}

    QTextEdit:read-only {{
        background-color: {COLOR_PALETTE['bg_secondary']};
        color: {COLOR_PALETTE['text_secondary']};
    }}

    /* ラインエディット */
    QLineEdit {{
        background-color: {COLOR_PALETTE['bg_input']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['default']}px;
        padding: {SPACING['sm']}px {SPACING['md']}px;
        color: {COLOR_PALETTE['text_primary']};
        selection-background-color: {COLOR_PALETTE['brand_light']};
        min-height: 32px;
    }}

    QLineEdit:focus {{
        border: 2px solid {COLOR_PALETTE['brand_primary']};
        padding: {SPACING['sm'] - 1}px {SPACING['md'] - 1}px;
    }}

    QLineEdit:disabled {{
        background-color: {COLOR_PALETTE['bg_secondary']};
        color: {COLOR_PALETTE['text_muted']};
    }}

    /* コンボボックス */
    QComboBox {{
        background-color: {COLOR_PALETTE['bg_input']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['default']}px;
        padding: {SPACING['sm']}px {SPACING['md']}px;
        padding-right: {SPACING['xl']}px;
        color: {COLOR_PALETTE['text_primary']};
        min-height: 32px;
    }}

    QComboBox:hover {{
        border: 1px solid {COLOR_PALETTE['border_dark']};
    }}

    QComboBox:focus {{
        border: 2px solid {COLOR_PALETTE['brand_primary']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: {SPACING['xl']}px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {COLOR_PALETTE['text_secondary']};
        margin-right: {SPACING['sm']}px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {COLOR_PALETTE['bg_card']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['default']}px;
        padding: {SPACING['xs']}px;
        selection-background-color: {COLOR_PALETTE['brand_light']};
        selection-color: {COLOR_PALETTE['text_primary']};
        outline: none;
    }}

    /* スピンボックス */
    QSpinBox, QDoubleSpinBox {{
        background-color: {COLOR_PALETTE['bg_input']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['default']}px;
        padding: {SPACING['sm']}px {SPACING['md']}px;
        color: {COLOR_PALETTE['text_primary']};
        min-height: 32px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 2px solid {COLOR_PALETTE['brand_primary']};
    }}

    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: {COLOR_PALETTE['bg_secondary']};
        color: {COLOR_PALETTE['text_muted']};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background-color: transparent;
        border: none;
        width: 16px;
    }}

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {COLOR_PALETTE['bg_elevated']};
    }}

    /* ラジオボタン */
    QRadioButton {{
        color: {COLOR_PALETTE['text_secondary']};
        spacing: {SPACING['sm']}px;
        padding: {SPACING['xs']}px;
    }}

    QRadioButton:hover {{
        color: {COLOR_PALETTE['text_primary']};
    }}

    QRadioButton:disabled {{
        color: {COLOR_PALETTE['text_muted']};
    }}

    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {COLOR_PALETTE['border_dark']};
        border-radius: 10px;
        background-color: {COLOR_PALETTE['bg_input']};
    }}

    QRadioButton::indicator:hover {{
        border: 2px solid {COLOR_PALETTE['brand_primary']};
    }}

    QRadioButton::indicator:checked {{
        border: 2px solid {COLOR_PALETTE['brand_primary']};
        background-color: {COLOR_PALETTE['brand_primary']};
    }}

    QRadioButton::indicator:disabled {{
        border: 2px solid {COLOR_PALETTE['border_light']};
        background-color: {COLOR_PALETTE['bg_secondary']};
    }}

    /* スクロールエリア */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}

    /* リストウィジェット */
    QListWidget {{
        background-color: {COLOR_PALETTE['bg_card']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['default']}px;
        padding: {SPACING['xs']}px;
        outline: none;
    }}

    QListWidget::item {{
        padding: {SPACING['sm']}px {SPACING['md']}px;
        border-radius: {RADIUS['sm']}px;
        color: {COLOR_PALETTE['text_secondary']};
    }}

    QListWidget::item:selected {{
        background-color: {COLOR_PALETTE['brand_light']};
        color: {COLOR_PALETTE['text_primary']};
        font-weight: 600;
    }}

    QListWidget::item:hover {{
        background-color: {COLOR_PALETTE['bg_elevated']};
    }}

    /* プログレスバー */
    QProgressBar {{
        background-color: {COLOR_PALETTE['bg_secondary']};
        border: 1px solid {COLOR_PALETTE['border_default']};
        border-radius: {RADIUS['default']}px;
        text-align: center;
        color: {COLOR_PALETTE['text_primary']};
        min-height: 24px;
        font-weight: 600;
    }}

    QProgressBar::chunk {{
        background-color: {COLOR_PALETTE['brand_primary']};
        border-radius: {RADIUS['sm']}px;
    }}

    /* スクロールバー */
    QScrollBar:vertical {{
        background-color: {COLOR_PALETTE['bg_secondary']};
        width: 12px;
        border-radius: {RADIUS['default']}px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background-color: {COLOR_PALETTE['border_dark']};
        border-radius: {RADIUS['default']}px;
        min-height: 30px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLOR_PALETTE['text_muted']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
    }}

    QScrollBar:horizontal {{
        background-color: {COLOR_PALETTE['bg_secondary']};
        height: 12px;
        border-radius: {RADIUS['default']}px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {COLOR_PALETTE['border_dark']};
        border-radius: {RADIUS['default']}px;
        min-width: 30px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {COLOR_PALETTE['text_muted']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        border: none;
    }}

    /* スプリッター */
    QSplitter::handle {{
        background-color: {COLOR_PALETTE['divider']};
    }}

    QSplitter::handle:horizontal {{
        width: 1px;
    }}

    QSplitter::handle:vertical {{
        height: 1px;
    }}

    /* メッセージボックス */
    QMessageBox {{
        background-color: {COLOR_PALETTE['bg_card']};
    }}

    QMessageBox QLabel {{
        color: {COLOR_PALETTE['text_primary']};
        font-size: 11pt;
    }}

    /* ステータスバー */
    QStatusBar {{
        background-color: {COLOR_PALETTE['bg_secondary']};
        color: {COLOR_PALETTE['text_muted']};
        border-top: 1px solid {COLOR_PALETTE['border_default']};
    }}
    """
