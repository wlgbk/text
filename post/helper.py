# coding: utf-8

from django.core.cache import cache

from common import rds
from common import keys
from post.models import Post

'''
更新缓存的策略
    主动更新
    主动删除旧缓存
    通过过期时间淘汰旧缓存
'''

def page_cache(timeout):
    def wrapper1(view_func):
        def wrapper2(request):
            if request.method == 'GET':
                key = keys.PAGE_CACHE_KEY % (request.session.session_key, request.get_full_path())
                print('PAGE_CACHE_KEY: %s' % key)
                response = cache.get(key)          # 先从缓存获取
                print('get from cache: %s' % response)
                if response is None:               # 缓存取不到
                    response = view_func(request)  # 直接执行 view 函数
                    print('get from view: %s' % response)
                    cache.set(key, response, timeout)  # 将结果存入缓存
                    print('set to cache')
            else:
                response = view_func(request)  # 直接执行 view 函数

            return response
        return wrapper2
    return wrapper1


def read_count(read_view_func):
    def wrapper(request):
        response = read_view_func(request)
        if response.status_code == 200:
            # 阅读计数
            post_id = int(request.GET.get('post_id'))
            rds.zincrby(keys.READ_COUNTER, post_id)
        return response
    return wrapper


def get_top_n(num):
    '''获取阅读排行前 N 的数据'''
    # ori_data = [
    #     (b'37', 15.0),
    #     (b'26', 13.0),
    #     (b'30', 11.0),
    # ]
    ori_data = rds.zrevrange(keys.READ_COUNTER, 0, num - 1, withscores=True)

    # rank_data = [
    #     [37, 15],
    #     [26, 13],
    #     [30, 11]
    # ]
    rank_data = [[int(post_id), int(count)] for post_id, count in ori_data]
    post_id_list = [post_id for post_id, _ in rank_data]  # 取出每一项的 post_id

    # 方法一
    #   错误的示范
    #   避免循环操作数据库，效率很低
    # for item in rank_data:
    #     post = Post.objects.get(id=item[0])
    #     item[0] = post

    # 方法二
    # # 批量获取 post
    # posts = Post.objects.filter(id__in=post_id_list)      # 根据 id 列表，取出所有的 post
    # # 根据 post_id 在 post_id_list 中的位置排序
    # posts = sorted(posts, key=lambda post: post_id_list.index(post.id))
    # # 逐个替换post
    # rank_data = [[post, count] for (_, count), post in zip(rank_data, posts)]

    # 方法三
    # posts = {
    #     10: <Post: Post object>,
    #     24: <Post: Post object>,
    #     26: <Post: Post object>
    # }
    posts = Post.objects.in_bulk(post_id_list)
    for item in rank_data:
        post_id = item[0]
        item[0] = posts[post_id]

    return rank_data
