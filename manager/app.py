import functools
import os
import traceback
from typing import Dict, Any
from datetime import datetime, timedelta
import csv
import io

from quart import (
    Quart, render_template, request, redirect, url_for, session, flash,
    Blueprint, current_app, jsonify
)
from astrbot.api import logger

admin_bp = Blueprint(
    "admin_bp",
    __name__,
    template_folder="templates",
    static_folder="static",
)


def create_app(secret_key: str, services: Dict[str, Any]):
    """
    创建并配置Quart应用实例。

    Args:
        secret_key: 用于session加密的密钥。
        services: 关键字参数，包含所有需要注入的服务实例。
    """
    app = Quart(__name__)
    app.secret_key = os.urandom(24)
    app.config["SECRET_LOGIN_KEY"] = secret_key

    # 将所有注入的服务实例存入app的配置中，供路由函数使用
    # 键名将转换为大写，例如 'user_service' -> 'USER_SERVICE'
    for service_name, service_instance in services.items():
        app.config[service_name.upper()] = service_instance

    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.route("/")
    def root():
        return redirect(url_for("admin_bp.dashboard"))

    @app.route("/favicon.ico")
    def favicon():
        # 返回404而不是500错误
        from quart import abort
        abort(404)

    # 添加全局错误处理器
    @app.errorhandler(404)
    async def handle_404_error(error):
        # 只对非静态资源记录404错误
        if not request.path.startswith('/admin/static/') and request.path != '/favicon.ico':
            logger.error(f"404 Not Found: {request.url} - {request.method}")

        # 为API路径返回JSON，为页面返回HTML
        if request.path.startswith('/admin/market/') and request.method in ['POST', 'PUT', 'DELETE']:
            return {"success": False, "message": "API端点不存在"}, 404
        return "Not Found", 404

    @app.errorhandler(500)
    async def handle_500_error(error):
        logger.error(f"Internal Server Error: {error}")
        logger.error(traceback.format_exc())

        # 为API路径返回JSON，为页面返回HTML
        if request.path.startswith('/admin/market/') and request.method in ['POST', 'PUT', 'DELETE']:
            return {"success": False, "message": "服务器内部错误"}, 500
        return "Internal Server Error", 500

    return app

def login_required(f):
    @functools.wraps(f)
    async def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("admin_bp.login"))
        return await f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    async def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            await flash("无权限访问该页面", "danger")
            return redirect(url_for("admin_bp.login"))
        return await f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        form = await request.form
        # 从应用配置中获取密钥
        secret_key = current_app.config["SECRET_LOGIN_KEY"]
        if form.get("secret_key") == secret_key:
            session["logged_in"] = True
            # 简单角色标记：现阶段使用同一密钥视为管理员
            session["is_admin"] = True
            await flash("登录成功！", "success")
            return redirect(url_for("admin_bp.dashboard"))
        else:
            await flash("登录失败，请检查密钥！", "danger")
    return await render_template("login.html")

@admin_bp.route("/logout")
async def logout():
    session.pop("logged_in", None)
    await flash("你已成功登出。", "info")
    return redirect(url_for("admin_bp.login"))

@admin_bp.route("/")
@login_required
async def dashboard():
    return await render_template("dashboard.html")


@admin_bp.route("/users")
@login_required
async def users():
    """显示所有用户列表"""
    # 从服务实例获取用户数据
    user_service = current_app.config.get("USER_SERVICE")
    if not user_service:
        return "服务未配置", 500

    users_result = user_service.get_all_users()
    if not users_result.success:
        users_list = []
    else:
        users_list = users_result.data

    return await render_template("users.html", users=users_list)


@admin_bp.route("/users/<user_id>")
@login_required
async def user_detail(user_id):
    """显示用户详细信息"""
    # 从服务实例获取用户数据
    user_service = current_app.config.get("USER_SERVICE")
    if not user_service:
        return "服务未配置", 500

    user_detail_result = user_service.get_user_detailed_info(user_id)
    if not user_detail_result.success:
        return "用户不存在", 404

    user_data = user_detail_result.data

    return await render_template("user_detail.html", user=user_data, user_id=user_id)


@admin_bp.route("/users/<user_id>/edit", methods=["GET", "POST"])
@login_required
async def edit_user(user_id):
    """编辑用户信息"""
    user_service = current_app.config.get("USER_SERVICE")
    if not user_service:
        return "服务未配置", 500

    if request.method == "POST":
        # 获取POST数据
        form = await request.form
        try:
            # 更新用户基本信息
            nickname = form.get('nickname', '').strip()
            level = int(form.get('level', 1))
            exp = int(form.get('exp', 0))
            coins = int(form.get('coins', 0))

            # 获取当前用户数据用于更新
            current_user_data = user_service.get_user_by_id(user_id)
            if not current_user_data.success:
                await flash("用户不存在", "danger")
                return redirect(url_for("admin_bp.users"))

            # 更新用户信息
            user_repo = current_app.config.get("USER_REPO")
            if not user_repo:
                return "服务未配置", 500

            # 更新用户数据
            user_repo.update_user_exp(level, exp, user_id)
            user_repo.update_user_coins(user_id, coins)

            # 更新昵称，如果提供了新昵称
            if nickname and nickname != current_user_data.data.nickname:
                # 直接更新昵称
                with user_repo._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users
                        SET nickname = ?
                        WHERE user_id = ?
                    """, (nickname, user_id))
                    conn.commit()

            await flash("用户信息更新成功", "success")
            return redirect(url_for("admin_bp.user_detail", user_id=user_id))
        except ValueError:
            await flash("数据格式错误，请检查输入", "danger")
        except Exception as e:
            logger.error(f"更新用户信息时出错: {e}")
            await flash("更新用户信息失败", "danger")

    # GET 请求 - 显示编辑表单
    user_detail_result = user_service.get_user_detailed_info(user_id)
    if not user_detail_result.success:
        return "用户不存在", 404

    user_data = user_detail_result.data
    return await render_template("edit_user.html", user=user_data, user_id=user_id)


@admin_bp.route("/shops")
@login_required
async def shops():
    """显示所有商店列表"""
    shop_service = current_app.config.get("SHOP_SERVICE")
    if not shop_service:
        return "服务未配置", 500

    shops_list = shop_service.get_active_shops()

    return await render_template("shops.html", shops=shops_list)


@admin_bp.route("/shops/<int:shop_id>")
@login_required
async def shop_detail(shop_id):
    """显示商店详细信息和商品列表"""
    shop_service = current_app.config.get("SHOP_SERVICE")
    if not shop_service:
        return "服务未配置", 500

    result = shop_service.get_shop_by_id(shop_id)
    if not result["success"]:
        return result["message"], 404

    shop_data = result["shop"]
    items = shop_data.get("items", [])

    return await render_template("shop_detail.html", shop=shop_data, items=items, shop_id=shop_id)


@admin_bp.route("/shops/<int:shop_id>/edit", methods=["GET", "POST"])
@login_required
async def edit_shop(shop_id):
    """编辑商店信息"""
    shop_service = current_app.config.get("SHOP_SERVICE")
    if not shop_service:
        return "服务未配置", 500

    # 获取商店仓库实例
    shop_repo = current_app.config.get("SHOP_REPO")
    if not shop_repo:
        return "服务未配置", 500

    if request.method == "POST":
        form = await request.form
        try:
            name = form.get('name', '').strip()
            description = form.get('description', '').strip()
            shop_type = form.get('shop_type', 'general').strip()
            is_active = int(form.get('is_active', 1))

            # 更新商店信息
            with shop_repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE shops
                    SET name = ?, description = ?, shop_type = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (name, description, shop_type, is_active, shop_id))
                conn.commit()

            await flash("商店信息更新成功", "success")
            return redirect(url_for("admin_bp.shop_detail", shop_id=shop_id))
        except ValueError:
            await flash("数据格式错误，请检查输入", "danger")
        except Exception as e:
            logger.error(f"更新商店信息时出错: {e}")
            await flash("更新商店信息失败", "danger")

    # GET 请求 - 显示编辑表单
    shop = shop_repo.get_shop_by_id(shop_id)
    if not shop:
        return "商店不存在", 404

    return await render_template("edit_shop.html", shop=shop, shop_id=shop_id)


@admin_bp.route("/shops/new", methods=["GET", "POST"])
@login_required
async def new_shop():
    """创建新商店"""
    shop_service = current_app.config.get("SHOP_SERVICE")
    if not shop_service:
        return "服务未配置", 500

    shop_repo = current_app.config.get("SHOP_REPO")
    if not shop_repo:
        return "服务未配置", 500

    if request.method == "POST":
        form = await request.form
        try:
            name = form.get('name', '').strip()
            description = form.get('description', '').strip()
            shop_type = form.get('shop_type', 'general').strip()
            is_active = int(form.get('is_active', 1))

            # 创建新商店
            with shop_repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO shops (name, description, shop_type, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (name, description, shop_type, is_active))
                shop_id = cursor.lastrowid
                conn.commit()

            await flash("商店创建成功", "success")
            return redirect(url_for("admin_bp.shop_detail", shop_id=shop_id))
        except Exception as e:
            logger.error(f"创建商店时出错: {e}")
            await flash("创建商店失败", "danger")

    return await render_template("new_shop.html")


@admin_bp.route("/shops/<int:shop_id>/delete", methods=["POST"])
@login_required
async def delete_shop(shop_id):
    """删除商店（设置为非激活状态）"""
    shop_repo = current_app.config.get("SHOP_REPO")
    if not shop_repo:
        return "服务未配置", 500

    try:
        # 将商店设置为非激活状态而不是物理删除
        with shop_repo._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE shops
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (shop_id,))
            conn.commit()

        await flash("商店删除成功", "success")
    except Exception as e:
        logger.error(f"删除商店时出错: {e}")
        await flash("删除商店失败", "danger")

    return redirect(url_for("admin_bp.shops"))


@admin_bp.route("/shops/<int:shop_id>/items")
@login_required
async def shop_items(shop_id):
    """显示商店商品列表"""
    shop_service = current_app.config.get("SHOP_SERVICE")
    if not shop_service:
        return "服务未配置", 500

    result = shop_service.get_shop_by_id(shop_id)
    if not result["success"]:
        return result["message"], 404

    shop_data = result["shop"]
    items = shop_data.get("items", [])

    return await render_template("shop_items.html", items=items, shop=shop_data, shop_id=shop_id)


@admin_bp.route("/shops/<int:shop_id>/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
async def edit_shop_item(shop_id, item_id):
    """编辑商店商品"""
    shop_repo = current_app.config.get("SHOP_REPO")
    if not shop_repo:
        return "服务未配置", 500

    if request.method == "POST":
        form = await request.form
        try:
            price = int(form.get('price', 0))
            stock = int(form.get('stock', -1))  # -1 表示无限库存

            # 更新商店商品信息
            with shop_repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE shop_items
                    SET price = ?, stock = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND shop_id = ?
                """, (price, stock, item_id, shop_id))
                conn.commit()

            await flash("商品信息更新成功", "success")
            return redirect(url_for("admin_bp.shop_items", shop_id=shop_id))
        except ValueError:
            await flash("数据格式错误，请检查输入", "danger")
        except Exception as e:
            logger.error(f"更新商品信息时出错: {e}")
            await flash("更新商品信息失败", "danger")

    # GET 请求 - 获取商品详细信息
    item = shop_repo.get_a_shop_item_by_id(item_id, shop_id)
    if not item:
        return "商品不存在", 404

    return await render_template("edit_shop_item.html", item=item, shop_id=shop_id, item_id=item_id)


@admin_bp.route("/shops/<int:shop_id>/items/new", methods=["GET", "POST"])
@login_required
async def new_shop_item(shop_id):
    """添加新商品到商店"""
    shop_repo = current_app.config.get("SHOP_REPO")
    if not shop_repo:
        return "服务未配置", 500

    item_repo = current_app.config.get("ITEM_REPO")
    if not item_repo:
        return "服务未配置", 500

    if request.method == "POST":
        form = await request.form
        try:
            item_id = int(form.get('item_id'))
            price = int(form.get('price', 0))
            stock = int(form.get('stock', -1))  # -1 表示无限库存
            is_active = int(form.get('is_active', 1))

            # 检查商品是否已存在商店中
            existing_item = shop_repo.get_a_shop_item_by_id(item_id, shop_id)
            if existing_item:
                await flash("该商品已经存在于商店中", "danger")
                return redirect(url_for("admin_bp.new_shop_item", shop_id=shop_id))

            # 添加新商品到商店
            with shop_repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO shop_items (shop_id, item_id, price, stock, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (shop_id, item_id, price, stock, is_active))
                conn.commit()

            await flash("商品添加成功", "success")
            return redirect(url_for("admin_bp.shop_items", shop_id=shop_id))
        except ValueError:
            await flash("数据格式错误，请检查输入", "danger")
        except Exception as e:
            logger.error(f"添加商品时出错: {e}")
            await flash("添加商品失败", "danger")

    # 获取所有可用的商品列表
    with item_repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_en, name_zh, description FROM items ORDER BY id")
        all_items = cursor.fetchall()

    return await render_template("new_shop_item.html", all_items=all_items, shop_id=shop_id)


@admin_bp.route("/shops/<int:shop_id>/items/<int:item_id>/delete", methods=["POST"])
@login_required
async def delete_shop_item(shop_id, item_id):
    """删除商店商品（设置为非激活状态）"""
    shop_repo = current_app.config.get("SHOP_REPO")
    if not shop_repo:
        return "服务未配置", 500

    try:
        # 将商品设置为非激活状态而不是物理删除
        with shop_repo._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE shop_items
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND shop_id = ?
            """, (item_id, shop_id))
            conn.commit()

        await flash("商品删除成功", "success")
    except Exception as e:
        logger.error(f"删除商品时出错: {e}")
        await flash("删除商品失败", "danger")

    return redirect(url_for("admin_bp.shop_items", shop_id=shop_id))