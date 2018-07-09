import requests
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings

from user.forms import RegisterForm
from user.models import User

from user.helper import login_required


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)  # 创建 user 对象，但是不提交到数据库
            user.password = make_password(user.password)  # 密码加密保存
            user.save()

            # 设置登录状态
            request.session['uid'] = user.id
            request.session['nickname'] = user.nickname
            return redirect('/user/info/')
        else:
            return render(request, 'register.html', {'error': form.errors})

    return render(request, 'register.html')


def login(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        password = request.POST.get('password')
        try:
            user = User.objects.get(nickname=nickname)
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': '用户不存在', 'auth_url': settings.WB_AUTH_URL})
        else:
            if check_password(password, user.password):
                # 设置登录状态
                request.session['uid'] = user.id
                request.session['nickname'] = user.nickname
                return redirect('/user/info/')
            else:
                return render(request, 'login.html', {'error': '密码错误', 'auth_url': settings.WB_AUTH_URL})
    return render(request, 'login.html', {'auth_url': settings.WB_AUTH_URL})


def logout(request):
    request.session.flush()
    return redirect('/user/login/')


@login_required
def user_info(request):
    uid = request.session['uid']
    user = User.objects.get(id=uid)
    return render(request, 'user_info.html', {'user': user})


def wb_callback(request):
    # 第一步: 获取授权码
    code = request.GET.get('code')

    # 第二步: 获取 access_token
    access_token_args = settings.WB_ACCESS_TOKEN_API_ARGS.copy()
    access_token_args['code'] = code
    resp = requests.post(settings.WB_ACCESS_TOKEN_API, data=access_token_args)
    data = resp.json()
    if 'error' in data:
        return render(request, 'login.html', {'error': data['error'], 'auth_url': settings.WB_AUTH_URL})
    request.session['access_token'] = data['access_token']  # 为了其他接口调用方便，将 token 存入 session

    # 第三步: 获取用户头像和昵称
    user_show_args = settings.WB_USER_SHOW_API_ARGS.copy()
    user_show_args['access_token'] = data['access_token']
    user_show_args['uid'] = data['uid']
    resp = requests.get(settings.WB_USER_SHOW_API, params=user_show_args)
    wb_user_info = resp.json()
    if 'error' in data:
        return render(request, 'login.html', {'error': data['error'], 'auth_url': settings.WB_AUTH_URL})

    # 取出获取到的平台用户信息
    platform_id = wb_user_info['id']
    platform_name = wb_user_info['screen_name']
    platform_icon = wb_user_info['avatar_large']

    # 根据平台 id 获取用户
    try:
        user = User.objects.get(platform_id=platform_id)
    except User.DoesNotExist:
        # 如果不能，创建一次，然后返回
        user = User.objects.create(
            nickname='WB-%s' % platform_name,
            age=18,
            sex='U',
            platform_id=platform_id,
            platform_icon=platform_icon
        )

    # 设置登录状态
    request.session['uid'] = user.id
    request.session['nickname'] = user.nickname
    return redirect('/user/info/')
