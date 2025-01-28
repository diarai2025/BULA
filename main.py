from flask import Flask, request, render_template, url_for, redirect, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Campaign, SubscriptionPlan
import os
from openai import OpenAI
import os
import base64
from PIL import Image
import io

app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app.config['SECRET_KEY'] = 'your-secret-key-here'  # Replace with a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def generate_image(business_name, description, keywords, platform='default'):
    sizes = {
        'instagram': '1080x1080',
        'facebook': '1200x628',
        'tiktok': '1080x1920',
        'youtube': '1280x720',
        'default': '1024x1024'
    }
    
    size = sizes.get(platform, sizes['default'])
    
    prompt = f"""Создай рекламное изображение для бизнеса '{business_name}' в формате {size}.
    Изображение должно содержать только продающий текст на чистом фоне.
    Текст должен быть крупным, контрастным и легко читаемым на русском языке.
    Основной текст: краткое описание преимуществ продукта/услуги.
    В нижней части добавь призыв к действию "Свяжитесь с нами сейчас".
    Стиль: Современный минималистичный дизайн. Ключевые слова: {keywords}."""
    
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",  # DALL-E API пока поддерживает только этот размер
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        existing_user = User.query.filter_by(email=request.form['email']).first()
        if existing_user:
            flash('Этот email уже зарегистрирован', 'error')
            return render_template('auth/register.html')
            
        user = User(
            email=request.form['email'],
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            phone=request.form['phone']
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неправильный email или пароль', 'error')
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

def create_notification(user_id, message, type):
    notification = Notification(
        user_id=user_id,
        message=message,
        type=type
    )
    db.session.add(notification)
    db.session.commit()

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/dashboard')
@login_required
def dashboard():
    # Check budget and create notifications
    for campaign in current_user.campaigns:
        if campaign.spend >= campaign.budget * 0.9 and campaign.budget > 0:
            create_notification(
                current_user.id,
                f"Кампания '{campaign.name}' достигла 90% бюджета",
                'budget'
            )
        
        # Check goals
        if campaign.click_goal and campaign.clicks >= campaign.click_goal:
            create_notification(
                current_user.id,
                f"Кампания '{campaign.name}' достигла цели по кликам",
                'goal'
            )
    # Здесь будет реальная логика получения данных из рекламных кабинетов
    # Это демо-данные для примера
    fb_impressions = 1200
    fb_clicks = 85
    fb_conversions = 12
    ig_impressions = 2300
    ig_clicks = 150
    ig_conversions = 25
    google_impressions = 1800
    google_clicks = 120
    google_conversions = 18
    
    analytics_data = {
        'fb_status': 'Активна',
        'fb_impressions': fb_impressions,
        'fb_clicks': fb_clicks,
        'fb_conversions': fb_conversions,
        'fb_ctr': round((fb_clicks/fb_impressions)*100, 2),
        'ig_status': 'Активна',
        'ig_impressions': 2300,
        'ig_clicks': 150,
        'ig_ctr': round((150/2300)*100, 2),
        'google_status': 'Активна',
        'google_impressions': 1800,
        'google_clicks': 120,
        'google_ctr': round((120/1800)*100, 2),
        'dates': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
        'fb_data': [10, 15, 8, 20, 12],
        'ig_data': [15, 20, 25, 18, 22],
        'google_data': [12, 18, 15, 22, 20]
    }
    
    # Calculate totals
    analytics_data.update({
        'total_impressions': fb_impressions + ig_impressions + google_impressions,
        'total_clicks': fb_clicks + ig_clicks + google_clicks,
        'total_conversions': fb_conversions + ig_conversions + google_conversions,
        'total_spend': 25000.50  # Example total spend
    })
    
    return render_template('dashboard.html', ads_enabled=True, **analytics_data)

@app.route('/toggle_ads', methods=['POST'])
@login_required
def toggle_ads():
    # Здесь логика включения/выключения рекламы
    return redirect(url_for('dashboard'))

@app.route('/toggle_campaign_status/<int:campaign_id>', methods=['POST'])
@login_required
def toggle_campaign_status(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return redirect(url_for('dashboard'))
        
    if campaign.status == 'active':
        campaign.status = 'paused'
    else:
        campaign.status = 'active'
    
    db.session.commit()
    flash(f'Статус кампании "{campaign.name}" обновлен', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_campaign/<int:campaign_id>', methods=['POST'])
@login_required
def delete_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return redirect(url_for('dashboard'))
        
    db.session.delete(campaign)
    db.session.commit()
    flash(f'Кампания "{campaign.name}" удалена', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_ads', methods=['POST'])
@login_required
def delete_ads():
    try:
        # Здесь логика удаления рекламы из рекламных кабинетов
        # Например, удаление из Facebook Ads
        access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        ad_account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
        
        if access_token and ad_account_id:
            from facebook_business.api import FacebookAdsApi
            FacebookAdsApi.init(access_token=access_token)
            
            # Логика удаления рекламы
            flash('Реклама успешно удалена', 'success')
        else:
            flash('Ошибка при удалении рекламы', 'error')
            
    except Exception as e:
        flash(f'Ошибка при удалении рекламы: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

with app.app_context():
    db.create_all()

def analyze_target_audience(description, keywords):
    prompt = f"""На основе описания бизнеса и ключевых слов определи целевую аудиторию.
    Описание: {description}
    Ключевые слова: {keywords}
    
    Опиши целевую аудиторию по следующим параметрам:
    - Возраст
    - Пол
    - Интересы
    - Уровень дохода
    - Поведенческие характеристики"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Не удалось определить целевую аудиторию"

def generate_keywords(business_name, description):
    prompt = f"""На основе названия бизнеса и описания сгенерируй релевантные ключевые слова для рекламы.
    Название: {business_name}
    Описание: {description}
    
    Верни только ключевые слова через запятую."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "реклама, маркетинг, продвижение"

def generate_ad_text(business_name, description, style, whatsapp, location, platform, budget):
    keywords = generate_keywords(business_name, description)
    target_audience = analyze_target_audience(description, keywords)
    prompt = f"""Создай привлекательный рекламный текст для бизнеса '{business_name}' для размещения на платформе {platform}.
    Описание: {description}
    Стиль: {style}
    Ключевые слова: {keywords}
    Контакты WhatsApp: {whatsapp}
    Локация: {location}
    Бюджет: {budget} Тенге
    Целевая аудитория: {target_audience}
    
    Текст должен быть креативным, запоминающимся и включать призыв к действию, 
    ориентированный на определенную целевую аудиторию."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Произошла ошибка при генерации текста: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

def publish_to_facebook(business_name, description, image_url, ad_text, location, whatsapp, target_audience, budget):
    try:
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.campaign import Campaign
        from facebook_business.api import FacebookAdsApi

        access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        ad_account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
        
        FacebookAdsApi.init(access_token=access_token)
        account = AdAccount(ad_account_id)

        # Create campaign
        campaign = account.create_campaign(
            params={
                'name': f'Campaign for {business_name}',
                'objective': 'MESSAGES',
                'status': 'PAUSED',
                'special_ad_categories': [],
            }
        )

        # Create ad set with location targeting
        adset = account.create_ad_set(
            params={
                'name': f'AdSet for {business_name}',
                'campaign_id': campaign['id'],
                'daily_budget': int(budget),
                'billing_event': 'IMPRESSIONS',
                'optimization_goal': 'CONVERSATIONS',
                'bid_amount': 2,
                'targeting': {
                    'geo_locations': {
                        'cities': [{'key': location}]
                    },
                    'age_min': 18,
                    'age_max': 65,
                },
                'status': 'PAUSED',
            }
        )

        # Create ad creative
        creative = account.create_ad_creative(
            params={
                'name': f'Creative for {business_name}',
                'object_story_spec': {
                    'page_id': os.getenv('FACEBOOK_PAGE_ID'),
                    'link_data': {
                        'image_url': image_url,
                        'link': f'https://wa.me/{whatsapp}',
                        'message': ad_text,
                        'call_to_action': {'type': 'MESSAGE_PAGE'}
                    }
                }
            }
        )

        # Create ad
        ad = account.create_ad(
            params={
                'name': f'Ad for {business_name}',
                'adset_id': adset['id'],
                'creative': {'creative_id': creative['id']},
                'status': 'PAUSED',
            }
        )
        
        return True, "Реклама успешно создана в Facebook Ads Manager"
    except Exception as e:
        return False, f"Ошибка при создании рекламы: {str(e)}"

@app.route('/subscription')
def subscription():
    try:
        # Create default plans if none exist
        if SubscriptionPlan.query.count() == 0:
            plans = [
                SubscriptionPlan(
                    name='Базовый',
                    price=15000,
                    campaign_limit=5,
                    description='Идеально для начинающих'
                ),
                SubscriptionPlan(
                    name='Бизнес',
                    price=35000,
                    campaign_limit=15,
                    description='Для растущего бизнеса'
                ),
                SubscriptionPlan(
                    name='Премиум',
                    price=65000,
                    campaign_limit=-1,
                    description='Максимальные возможности'
                )
            ]
            for plan in plans:
                db.session.add(plan)
            db.session.commit()
        
        plans = SubscriptionPlan.query.all()
        return render_template('subscription.html', plans=plans)
    except Exception as e:
        return str(e)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        amount = request.form.get('amount')
        
        if payment_method == 'kaspi':
            # Здесь будет логика для Kaspi QR или переадресация
            return redirect('https://pay.kaspi.kz/pay/0q9xslpw')
        elif payment_method == 'bank':
            # Логика для банковского перевода
            flash('Пожалуйста, используйте реквизиты для перевода', 'info')
            
        return redirect(url_for('dashboard'))
        
    return render_template('payment.html')

@app.route('/subscribe/<int:plan_id>', methods=['POST'])
@login_required
def subscribe(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    # Here you would integrate with a payment gateway
    # For demo purposes, we'll just activate the subscription
    current_user.subscription_id = plan.id
    current_user.subscription_active = True
    db.session.commit()
    flash(f'Подписка {plan.name} успешно активирована!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/create_campaign')
@login_required
def create_campaign():
    if not current_user.subscription_active:
        flash('Необходимо оформить подписку для создания рекламных кампаний', 'error')
        return redirect(url_for('subscription'))
        
    plan = current_user.subscription
    if plan.campaign_limit != -1 and len(current_user.campaigns) >= plan.campaign_limit:
        flash(f'Достигнут лимит рекламных кампаний ({plan.campaign_limit})', 'error')
        return redirect(url_for('dashboard'))
    
    campaign_number = len(current_user.campaigns) + 1
    session['campaign_name'] = f"Компания {campaign_number}"
    return render_template('index.html', campaign_name=session['campaign_name'])

@app.route('/view_campaign/<int:campaign_id>')
@login_required
def view_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    return render_template('result.html', 
                         ad_text=campaign.ad_text,
                         business_name=campaign.name,
                         generated_image=campaign.image_url)

@app.route('/update_goals/<int:campaign_id>', methods=['POST'])
@login_required
def update_goals(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return redirect(url_for('dashboard'))
        
    campaign.impression_goal = request.form.get('impression_goal', type=int)
    campaign.click_goal = request.form.get('click_goal', type=int)
    campaign.conversion_goal = request.form.get('conversion_goal', type=int)
    campaign.roi_goal = request.form.get('roi_goal', type=float)
    
    db.session.commit()
    flash('Цели кампании успешно обновлены', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_campaign/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
def edit_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        campaign.name = request.form.get('name')
        campaign.ad_text = request.form.get('ad_text')
        campaign.budget = request.form.get('budget')
        campaign.location = request.form.get('location')
        campaign.style = request.form.get('style')
        
        db.session.commit()
        flash('Кампания успешно обновлена', 'success')
        return redirect(url_for('view_campaign', campaign_id=campaign.id))
        
    return render_template('edit_campaign.html', campaign=campaign)

@app.route('/generate', methods=['POST'])
def generate():
    business_name = request.form.get('business_name')
    description = request.form.get('description')
    style = request.form.get('style')
    whatsapp = request.form.get('whatsapp')
    location = request.form.get('location')
    platforms = request.form.getlist('platform')
    if 'all' in platforms:
        platforms = ['instagram', 'google', 'tiktok', 'youtube', 'yandex', 'facebook']
    platform_str = ', '.join(platforms)
    budget = request.form.get('budget')

    ad_text = generate_ad_text(business_name, description, style, whatsapp, location, platform_str, budget)

    # Генерируем несколько вариантов длины
    short_version = ' '.join(ad_text.split()[:20]) + '...'

    # Generate keywords and platform-specific images
    keywords = generate_keywords(business_name, description)
    platform_images = {}
    for platform in platforms:
        platform_images[platform] = generate_image(business_name, description, keywords, platform)
    image_url = platform_images.get('default', platform_images[platforms[0]])
    
    target_audience = analyze_target_audience(description, keywords)
    # Публикуем в Facebook если выбран
    facebook_status = None
    if 'facebook' in platforms:
        success, message = publish_to_facebook(
            business_name, 
            description, 
            image_url, 
            ad_text, 
            location, 
            whatsapp, 
            target_audience, 
            budget
        )
        facebook_status = message

    if current_user.is_authenticated:
        campaign = Campaign(
            name=session.get('campaign_name', business_name),
            user_id=current_user.id,
            ad_text=ad_text,
            image_url=image_url
        )
        db.session.add(campaign)
        db.session.commit()
        
    return render_template('result.html', 
                         ad_text=ad_text,
                         short_version=short_version,
                         business_name=business_name,
                         generated_image=image_url,
                         target_audience=target_audience,
                         facebook_status=facebook_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)