from datasets import Dataset, Split

from plugins.location_tools.repo_ops.repo_ops import explore_tree_structure, set_current_issue, get_entity_contents


def main():
    # bench_data = Dataset.from_json('dataset/product_backend.json', split=Split.TEST)
    bench_data = Dataset.from_json('dataset/product_backend_6677917fd7.json', split=Split.TEST)
    set_current_issue(instance_data=bench_data[0], rank=0)

    # start_entities = ['allv2/application/activity/list/stock_process_task.go:buildStockResp']
    # direction = 'upstream'
    # start_entities = ['allv2/application/activity/list/stock_process_task.go:StockProcessTask.Process']
    # start_entities = ['handler.go:ProductBackendServiceImpl.GetSchema']
    start_entities = ['allv2/application/view/component_manager/component_manager.go:ComponentManager.RenderElements']
    direction = 'downstream'
    tree_content = explore_tree_structure(start_entities=start_entities,
                                          direction=direction,
                                          traversal_depth=50,
                                          dependency_type_filter=['invokes'])
    print(f'{start_entities}的{direction}依赖如下: \n{tree_content}')

    # content = get_entity_contents(["allv2/application/activity/list/stock_process_task.go:StockProcessTask.Process"])
    # print(f'文件内容如下：{content}')


if __name__ == "__main__":
    main()
