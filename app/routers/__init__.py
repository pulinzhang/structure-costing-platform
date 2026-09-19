"""Router 层包。各切片模块导出名为 router 的 APIRouter，由 bootstrap 扫描注册。

路径参数（零例外，api-type-safety.mdc §6）：
- 整数：必须 /{name:int}，禁止裸 /{name}。
- 字符串键：必须同 APIRouter，且全部静态路径写在参数路径之前。
- 守卫：python -X utf8 -m scripts.check_route_path_params
"""
