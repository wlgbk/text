# coding: utf-8
from django.shortcuts import redirect


def login_required(view_func):
    '''检查用户登录的装饰器'''
    def check(request):
        uid = request.session.get('uid')
        if uid is None:
            return redirect('/user/login/')
        else:
            return view_func(request)
    return check
