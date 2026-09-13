/**
 * @file    test_sts3032.c
 * @brief   STS3032 封包 PC 测试 (校验和 + 帧格式)
 *
 * 编译: gcc -o test_sts3032 test_sts3032.c sts3032.c
 */

#include <stdio.h>
#include "sts3032.h"

static int g_fail = 0;
#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("  [FAIL] "); printf(__VA_ARGS__); printf("\n"); g_fail++; } \
    else         { printf("  [ OK ] "); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

int main(void)
{
    printf("========== STS3032 封包测试 ==========\n\n");

    /* 2 个舵机: ID1 pos=2148 spd=300 acc=30, ID2 pos=1948 spd=300 acc=30 */
    StsServoCmd cmds[2] = {
        {1, 2148, 300, 30},
        {2, 1948, 300, 30},
    };
    uint8_t buf[64];
    int len = sts3032_build_sync_write(cmds, 2, buf);

    /* 1. 帧头 */
    printf("[1] 帧头\n");
    CHECK(buf[0]==0xFF && buf[1]==0xFF && buf[2]==0xFE,
          "帧头 FF FF FE 正确");

    /* 2. 长度字段 */
    printf("\n[2] 长度字段\n");
    CHECK(buf[3] == 20, "LEN = 20 (实际 %d)", buf[3]);

    /* 3. 指令 + 地址 */
    printf("\n[3] 指令/地址\n");
    CHECK(buf[4]==0x83 && buf[5]==41 && buf[6]==7,
          "SYNC_WRITE(0x83) + ADDR(41) + NLEN(7) 正确");

    /* 4. 位置小端编码 */
    printf("\n[4] 位置编码\n");
    /* ID1 在 buf[7], 数据 buf[8..14]; 位置在 buf[9](低) buf[10](高) */
    CHECK(buf[7]==1 && buf[9]==(2148&0xFF) && buf[10]==((2148>>8)&0xFF),
          "ID1 位置 2148 小端正确 (0x%02X 0x%02X)", buf[9], buf[10]);

    /* 5. 校验和 */
    printf("\n[5] 校验和\n");
    {
        uint8_t sum = 0;
        for (int i = 2; i < len - 1; i++) sum = (uint8_t)(sum + buf[i]);
        CHECK(buf[len-1] == (uint8_t)(~sum),
              "校验和正确 (0x%02X == ~0x%02X)", buf[len-1], sum);
    }

    /* 6. 总长度: 7 帧头 + N*8 数据 + 1 校验和 */
    printf("\n[6] 包长度\n");
    CHECK(len == 7 + 2*8 + 1, "总长度 = %d (7 + N*8 + 1)", len);

    printf("\n========================================\n");
    if (g_fail == 0) { printf("全部测试通过 ✅\n"); return 0; }
    else { printf("%d 项失败 ❌\n", g_fail); return 1; }
}
