#import <Foundation/Foundation.h>

NSString* ModifyString(NSString* src)
{
    return [src stringByAppendingString:@"foobar"];
}

int main()
{
    NSString* aString = @"Hello world";
    NSString* anotherString = @"Let's be friends";
    ModifyString(aString);
    ModifyString(anotherString);
    return 1;
}
    