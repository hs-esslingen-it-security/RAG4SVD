/*
 * vuln_04_integer_overflow.c
 * 漏洞类型：整数溢出 (Integer Overflow) 导致堆溢出
 * count * sizeof(Item) 在大 count 时回绕为小值，malloc 分配过小缓冲区。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int   id;
    float value;
    char  tag[16];
} Item;

typedef struct {
    Item *items;
    int   count;
    int   capacity;
} ItemList;

/* 漏洞：count 未做上界校验，乘法可能溢出 */
ItemList *create_list(int count) {
    ItemList *list = (ItemList *)malloc(sizeof(ItemList));
    if (!list) return NULL;
    /* VULN: count * sizeof(Item) 可能整数溢出 */
    size_t alloc_size = count * sizeof(Item);
    list->items = (Item *)malloc(alloc_size);
    if (!list->items) {
        free(list);
        return NULL;
    }
    memset(list->items, 0, alloc_size);
    list->count = 0;
    list->capacity = count;
    return list;
}

int add_item(ItemList *list, int id, float val, const char *tag) {
    if (!list) return -1;
    if (list->count >= list->capacity) {
        printf("List full\n");
        return -1;
    }
    /* VULN: 如果 capacity 因溢出而实际很小，这里越界写 */
    Item *it = &list->items[list->count];
    it->id = id;
    it->value = val;
    strncpy(it->tag, tag, sizeof(it->tag) - 1);
    it->tag[sizeof(it->tag) - 1] = '\0';
    list->count++;
    return 0;
}

void print_items(const ItemList *list) {
    if (!list) return;
    for (int i = 0; i < list->count; i++) {
        printf("  [%d] id=%d val=%.2f tag=%s\n",
               i, list->items[i].id, list->items[i].value, list->items[i].tag);
    }
}

void free_list(ItemList *list) {
    if (list) {
        free(list->items);
        free(list);
    }
}

float sum_values(const ItemList *list) {
    float total = 0.0f;
    for (int i = 0; i < list->count; i++) {
        total += list->items[i].value;
    }
    return total;
}

int main(void) {
    /* 正常用法 */
    ItemList *normal = create_list(10);
    add_item(normal, 1, 3.14f, "alpha");
    add_item(normal, 2, 2.72f, "beta");
    print_items(normal);
    printf("Sum = %.2f\n", sum_values(normal));
    free_list(normal);

    /* 漏洞触发：传入极大的 count，导致整数溢出 */
    int evil_count = 0x40000001;  /* 乘 sizeof(Item)=28 时溢出 */
    printf("Attempting to create list with count = 0x%x\n", evil_count);
    ItemList *evil = create_list(evil_count);
    if (evil) {
        /* 写入时实际缓冲区远小于 capacity，触发堆溢出 */
        for (int i = 0; i < 5; i++) {
            add_item(evil, i, (float)i, "x");
        }
        print_items(evil);
        free_list(evil);
    }
    return 0;
}
