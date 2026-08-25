void kernel_main(void)
{
    for (;;) {
        __asm__ volatile ("hlt");
    }
}