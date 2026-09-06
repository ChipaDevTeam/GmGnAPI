"""
Tests for the SRP-6a client used by GMGN's email/password login.

The vectors below were produced by the JavaScript secure-remote-password
package (v0.3.1) that GMGN's web app bundles, driving both its client and
server halves. They pin the exact bytes GMGN expects, so a refactor that
changes hex padding or hashing order fails here rather than in production.

Regenerate with:

    npm install secure-remote-password
    node -e '...'  # see docs/ for the generator used
"""

import pytest

from gmgnapi import srp


# Each case: derived from the JS implementation, including a full client/server
# round trip so the server proof (M2) is a real one.
JS_VECTORS = [
    {
        "salt": "c9",
        "username": "alice@x.com",
        "password": "pw",
        "privateKey": "b756fce8869c0ad3faab4c65ea0c9cb4bb5258da57e0ff6ee428533fab09223b",
        "verifier": "2fa14745352a6f8e9f84f98d03d8164b3aa0671a3d280f0af68893b62fb62f890493a35eb13f47ed164cf90c49ba119025f8390ffbe7832707834dd070694d56b228c2fa9be7103e6bc2ff6f3af07d81a07e36656de1888f3e1b196fac814f195a5d43cbb43fee0001d94a2e049f66aba434e3083acf74f553c3a8bd1060342f954a1cef463a814638b84bb09e9a1e727c617f0a9b202276a9f2732aea237b4be6fa1db5fa9db73ecaaab1a76371ccc6a5d9f91a66d56a9e921f305b0ada35c9dc4c7f90b37bc2c10c760f5a0ca3e52d6a36b110a1a584aa4904856dd59a998ce6a06916c20459afe6eba23b4a67f3f4ad91c1174cfafb200b9e54dd4bbcdc60",
        "clientSecret": "196679fe7caab99cb63461828d25510adfe8a12bb9d09e201f360323d3130f94",
        "clientPublic": "535b004eff23f6b8bdf5c5ce5914bf69f0027437b88ebb9c3acc9ca29031916609e1ad50e027cff7fa9ab29f215b15113f98716e8662cf8ae0ff58f69ba5037d7b602c5c19dbd832c9cfe6937d4eaf88759c6d5ea5d30fea907a7a065aeae88f5731b527f34a7af54957846b3a47ad14810324c664ecf04938db53f568c52ad44d7ffdda7d25d0d209693cf95df8a985bdfaf4d744b30fada37d9d402dc18f9d24432e20f64156570a13277ac9dfd58282dca5a6875014ec141a83e1c67fbca389a0cd8b6cb3064c672fe8ab3bb00e42bea9e9330706d655d2c7c1b9e869eb4e4b82289be449036df2beb8e4cc5e47eadab70ccac383d85ff09feda89079bf33",
        "serverPublic": "0f60cb68915e526395510000c692de52871b252128a4d2c34a90db309a88774f435add6922d3f19e670332f86561e88f4edd7614e94f6d295a6f39ffa95b0bbf849bfbfcb5b1a9c7abff4680ad64830895d3f3406b4e015d54341e8be677c9ab003d85cb94e3aeb3a93b2460dcb50959b6e49ba698c524ec4e91f25f8219f46278a77b747e7929e213a9c2358b3d19a482c4d109216d841d4f9659467fcafca1371de9f32b6d07e8e63d67755a4698b950d6604c474f1da71dad6039c9208c9c8f511f3521d3ded9ae2a31738cd8603ffc98919681048e34117fec23bf310146f5bee494345dc85763d4c16e793611c61a75c426cdd74502d69cceec0fdc8498",
        "sessionKey": "7ad83a37d5707aa65b71ccbdd2a90798ae593731cc7ed705247dd2813f93ce71",
        "proof": "c4c05183883d3a3d221f22004c44f2c32358c4dd9681bc16f4e5483893cb94fa",
        "serverProof": "bff28e2e79b11018bec8f35837e5a2fc3dc56d3f488c7bb15234a6bea770cc61"
    },
    {
        "salt": "d5cb",
        "username": "BOB",
        "password": "",
        "privateKey": "68e17c0b2d27b3dea10ef75bfbfd8c54b821396a00804085d6d36012f206002b",
        "verifier": "1877e08f27330d3c0dabf38223238fcd7f4e6cf39a0ca0ca4b4d741ca0d65d97d4bdc0ee1d89fa508d20e08e7065f75e465e20bf2095b28d2820876dca9d1b64159bfe22a66e1608c079ed9d3190122e8f845dee0ef0531e674fbe2739058e373689f8d7dcebbc76d050bdde5f99af27fe7426643513f866c70e36effa03ae7ac7a251f99c05bb60e78b4b69f5ab346865bc72118e74c27a4c25409369cffe944c6e6533d59f7f5db5f97399e83d8ce9736967892657bb1a065f7d4ca1d55a32d448d83e142cdf4de2d04a7ed867cf363d874bcca989f1e2746732ffa4185e88698f55a1642509c1ac2dcff1b7ce3850cf4ca1fa7069ef1897c3eb536f59b40b",
        "clientSecret": "c615e6de15abcebd5d90dead31aa60ac2296b320adc1d7070daf9afa078e42da",
        "clientPublic": "5f42e2d7df2ac2e089477091e7aeee0357414ee27f918f52ef63c4d7854683d0af9f149881f67ac6da93690a6c43ea784fdd9d02ff7ab5514908944a7c5389b240fd7d95c062e8e980138cddc46dc3990a183ffb623fa7bc9b6bca479884e357c937620606fda2bafa5dcd05f7aaea2f04fced8679beffa6a25617395a8f7c69866b6c599a8c5288f7c1ec1630435ee1abe1d4b8e097936eec8a7edf8392a504f1b9d87c22d00680af1e001099b4d91f7f310902b04c7c8d1d9d24035774ad0dd1423d3aa22a73110da4f5733e4937d7fcb5aa91413a4fbbd6b2f1d89d1b26dd39a3fc9a9cbe13213b49812a42d8783cf964b38f5d2c55548d31a29ed5123bd8",
        "serverPublic": "172724a096092a81e52040a0e063f12b02e1f5ad5a755ce4b8ba720dce10e999f5870b0d88cf331ff9e7e909c82bef95d6b13755281d62baf3a95421bf39d624230bda347ac914cacf516d9e6244ee2e0e1ee60a108b6d0fd8aa08c217c2deb33b76463076825ec3934c66e56357b5544b16a0039ebbc1b8e95b9e7659f00bd65d41430a0f871fc9c12182342e91d3afd723d22df20cdc04bb58e898d9f0fe5dfbbfdbcd055df563094cc4d1e380835614dd9c29b98c5f708c7cc2547f21f030ace74cf469dfdd3c9c5a767ccdf6287773d870f0979419b7416550881771ef92d2d8b5b1d643cb28e4839ba9c92e8cced4b8a599731013cee2f6f93cf3314d23",
        "sessionKey": "497e0500d6dbfd678bc1152c0a366c1efc18c702c2de1febaf719c42d3d231eb",
        "proof": "b34d5f8bebf9e54a856e8c627432d63018bf19f5accfc9b1086052e25898384f",
        "serverProof": "b86ec5a9f1c682dfb91be7ee425df28325793adcd18caeddd1004fff8b08334b"
    },
    {
        "salt": "41a390",
        "username": "üñí🔐",
        "password": "p@ss wörd 🔐",
        "privateKey": "11a8ad28c30f5fae4b771939d9ede303dc59600eeee19ece6404c959071f7153",
        "verifier": "73198c6e38d67de49ec16287d082493e391eda68edb7303a3d61d673982c2ad550a654daad7b409a573f12c023a80f408598225249fc955756661e9fe950a1d0b8fa2a46a32b5a59a1432e87dd0e95be50ff05afce9927c61e5ed0c6153e975881bc5c6a3256dd84818d686cc807bd2bc1341ec3eeff367d8c8c81ef7afef884eff520f879548bbabb8f1bebfc792a9dee59c4807ff0073259860b02ae34e5e932b20b79325e9614ba47d669a465093db939af289e2153139bf5e6a3e42bb9a3e8282939797b3837dcd77ecbbe8eb69a6409fe20f28fe0dc45677a04288d0655aee9a9a8b328bbd7fc224c885b74d3e6f3f1a69cb365ce74ab48d5538c717ccc",
        "clientSecret": "4c4d5e72a5885d307f7eabf13b627357b0c12c211bd7ad36e49aeacca4a3e5cc",
        "clientPublic": "7d5ef398d3f0b6f0ad8eb9486873911688b371e6f71cc725040eddb2bb328253740d4af56aaf46abd5e091d5f2a59d3208cd893c82e3db8926505c862e633be7d646af37092e2cdac47a909cb174003bf57b00fe091b640128b53b3f7440a4cd9e933e35e3575b5a3671ba91067a6f0c3fa71c66319664f875389ca3747ea21ee2932723b41eeab068c7e32a5e01aa6e16457305a5c954c46d336d29f350d6c6b9b603954ef559c21fc5c0c814a0c40ec312a3879445fe50a3f0953e88f56eafc787ffcae67054370c9358bfba0657a4aabb40db5c7880266686e9a72c721538eb081d3495e5c029addee1a18f4a0fa6fb113e964a025b87167d843c000c756f",
        "serverPublic": "7d7e9b22f3acff6d8fc0bf0c2232f08002ca8a1e7842a120bae0d7fac974762b7b1ed3274f91e94d05e87bbb16c25c6677454c2586522f0fbf040149a79bb99e888b1f736f0c4197028567973ae2c0e577689b7cef91fbcce6662c08b46296d7fb9c39e9dc25370a607d4bee3189bccc5d0077f2019373a0108e4ee30c0aea2cfa663a6b1a8d130988aacb713c46095f8df6ec87272a1b545382d5de00ed565935ed2e64d7975b198816c8cdc5f28a3bbc5247fc344acd5d59199a373ecaacfb1a6fadb4c671639ff65ae2d2f14e2f598f952ae01759fe29439c9eea95b71a6659e6c293c822d97c92a3e68b28aed095de40132d411cd7bb19b841059d8d5d17",
        "sessionKey": "152f6a575720dd2dc2cf8007eca5c84204b0f2f181ea01db7170890ddf982064",
        "proof": "732fb90cdbbfcb392fb50eeef02041f1f68ce200a7a5e7d92841f8f51f48bf89",
        "serverProof": "2fafce87062379feeb0f60cb9b31527f024fe65462a0daa751a93800e14a7122"
    },
    {
        "salt": "aafe4e22",
        "username": "",
        "password": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "privateKey": "3c8ffd259a4c974c2ae31b6a0d75cf50e9295e983f43f5958752c2f3a5e0e913",
        "verifier": "1264973c67e0aa718985b0cacd1bf807f4050eb2708fb7266f075a04f65d6b85db971a060289352b7a62589b4e1ce2e010d259f5aeb5422cbae26bb1c3d835810882634f8b6bfa4d0b81b2556a27f4a191bb358231b147b9dc7cebf40d1868bac0c7d4eb1eafa0430f7f5da0cd1212ff5f4fd9598c38d549f1f620af657da677358a3a9252afe7ba1884f7af88b234db947104355e6afd7d87e8845ade0eeda42b2fe8de8f12ebca10ab05b99a8d2a0e06bc9e28383dea32f7d675a74ed33c9e5e69db9a55d3866f8a299380b57796d823fa78e501423c18196ed275cd41623d26cf9e0d7286b39e1851021d39a0cacf1f31f688c9c5fdca39809fbf3b9dcdf0",
        "clientSecret": "cdc084bc235530094541d4e97dc536e3807251129bc575d1928ed358c2f22ee6",
        "clientPublic": "a43fd9898a8303015d73906f293dafb02252fd9e50a6de6f1a4bcc09eac17d8b721323bd9e5914c832ecba428a9d5424cefe3dc9e075a5018967f724fc3c402f69a9a287a55c070703b6403ae0980443194115cfada09104408c627089aa87fdc3781fdfedf6d48dbe78595cb95442167bcff5c237a4ddd35d64d81c9785c3cb9a145a03b4719f7a5887e3750f2b32575f48ed4c02a6a9ccf4ab624bc3be2fdd96a2266d2204e983529d0e9554700c7e33c52929d8cd144cf2901da364398fe93f9f3b57f146c6101fcd80f9e5a5357ccc321b21d88a9f4b0fa27ae7cdff140d3d6fb803e193a9cddb2f25f12107a2923ee02c5614e97cd305952241f95f2f21",
        "serverPublic": "7a1aa7f669141822d8e92048bb3b5bba382850c8cd2ca5a266299c9179bee081d7fe4994c38813874fc348eff11452ac79a186ecf07f82e93f399fdf85464eaf8cca3b00be6c1bf0bb8546afc953a58ecd211ef3e28a99f1a6848c61d9cfea32a93c3c87e7d31935dd425de03f772b1e1a2af2d2f270504ae811a7b75f718c483490ba04ace96302047ddaefd1f18ec954581ca794371240f678185a64631e353756452cd8a05a57ab90fd280c6bbd928b17532732f577d51d194f707f424631cc118592a9fb0f07b5d2f5e3e8cb383060e81d452f79013cd56c8a9085bf3d4cf0810cb57b8b02eada0cadc88248605570f860ca95413ffbcdefad0f6f199f3c",
        "sessionKey": "ae33ac75d8b608f2974117380f05aa69ee236358ff7f1a2ab64107ce442edbd3",
        "proof": "3be20e4cc6f82ab164b54b18b18ef5544d759846fc6a33d51e0c9581b400a000",
        "serverProof": "982d266da33dec85fa0409f698c39cba84db61e7cad54c5fa1e94d2d95bab5d6"
    },
    {
        "salt": "b93677cf030ca65f",
        "username": "BOB",
        "password": "",
        "privateKey": "a5df090db7308008420f75399c8043b77d3b714a0ad440da42a7271152973b1d",
        "verifier": "ab5d12aa6158684ca69d848813cb92ea17d7272fce739d4c84859e5dc9f0b305fa7e5f891ae79f3611aac80af35ab4a7e0f32f2cc0ac5fa8018a895c0121cd5b68b6f35c4e733f0e6a792cea008e43cd56077760abd36f6e078bea553bee891a1a2ada3d18a472353b8df3933a0ee2626f3f84f17aefaec503ec90bf6b51b4d9b9e5d7863f06c13531260a8f7c6cec4f1d7c4259fbd15bc2453486aa69a353ba1144b99045625120477e15c70f7be19b6e47cd787c5d6a95cf58eaa404b4dbd902649c71b6cda92f24b65fe37d6d8edf4e1434379ffd2b15a74f419731e1864adf398f818ed1d27a0866aa9a7dddf0113b427b0a2b840063615e9a0d1751b654",
        "clientSecret": "2ecd6b2e2361a3d0004070200f1c3b320edf57fc220b7cd7f32f2a8172079e4f",
        "clientPublic": "6d6109e0db7e3b77ff5f26e6acebbee18b6be3055806f55b7f60af3740b8abc756c6fff588664687765ba91fce0061db60c10688c6365dd032d6877f586aa1ffcc35f7519722e231ceb58e15872d0ca46a4c80e2bc1348d7bec623a830dd774cbd1df7db459ce3f697215a1d09b18257d125e3384917d9e07cfd23d093f40b3f51cb7e5b404daf12da6a8d840ca439151ea5b2c79e77f19db05402452020f7cbd2498045cfb298e6f0a418122cfabb2192dd517b1797f1cd0e9ec7630e4e3ccba36b2e5941b895efe1e537f0bb891815c6b42b5071935090d198f7964905a4423b77d0b99713ef62efdd49499703b5377e45de96f5d153e6d23d4ac6237052b3",
        "serverPublic": "8ed86da83b1a00200dadc76ed74bd57fc5695d857e2b63e3c44eca4292067aafc548937d9141c1ac5ad65c709276a3239b603148bf4443e3255dfa56641c36207967ed8d2089587e7704fbe409afcaa452e2ff32c738bba4147b17d0b019d60359372de5c7755c1df6a777009888d487bdcd453c67c32900dfa57f13fb586e5f842d57062f08b68266516b2da5509844409188c38580d01199492f7a2c41062f8ab2ca1f9a36375eec406ea73830a1efc03a14a776ceec0783736f87cd138a65f9dd1de1d1c30b9dc390b5229cda4977e217b7788ad848e6bff03d9f3071777d3fb41c8fc3aa1c071679523a8452c783b573cb849661577b21040ff3519085c4",
        "sessionKey": "484fd7e9f195c4ef295098da0fadfd41a469743de6b8f9f478a291ff0c87edf1",
        "proof": "42abcd9e4958c0fc9c2c42c4203399c0753571604b2ae52b422a88822baee09c",
        "serverProof": "4ca032e12f73a81fa554b5089ae5493b1f7533c728b37e1b82a2022097e1df80"
    },
    {
        "salt": "6c3a282508b38a21ad8609e5",
        "username": "x:y:z",
        "password": "c184a1242121f5c0",
        "privateKey": "fd929f2e3650fdabd05f0ccfef5144835cf4444ef7055d89c83243b1b492bfd0",
        "verifier": "95008a3885ff766c49e95c10830c623f57264d1a01c5bdda643613881b72c24fea5ebab9f63ceb28d17ae3644799671f5566da0085e5ac0b0c72e02f6696daa7d71f1458901cbffa95e04e34fa9eaf4b1aa3feb06b597242b3f398aef71c770bbd0ccc8fce49be57d0739ee843d99f71566c5007c5b0a4cbced4510b9591efc184e931a5822692c0018670ba2e9e8ec3e092b0ed93d600c0b28566beabd8c9457a08610a6ae0247d2a02c613981f9a2902f94fcbd1aea78c624689ecdb49cc64f8183913be35e911ebf87f5edbeb89123c6113dd75c21f34c2c22d5e4b9c73308a1e63551adcefa910cbe582bb18ea0239ad24cdaf916aed8b3cadfd349421c4",
        "clientSecret": "72a75415d4d0a3a055f52f8608f10572a75e2524a66979177b252a5997177bcb",
        "clientPublic": "4e899e3fb0f540cded62265fe79b2693331d415a059a522a51b949348811cb8f9ca07b63181c6def551e7da25766a1d494d6d38998307067f5480daf7ff485a2b9cd0b42a5a5a1e6f6aafe2158e2c5214d595ef32652bd58234116035626a282e44d78cd334cf98c80758d9a07965bfba6a9f6c4dba80a1abc241ce41eb9e217f6f09a5af252c32cd058c774222c6cd9962fcb7a2b5a79f61b33d75cab4c50ea52bcfd1a17e603bd82bd907fe235c289f7ce7c48075931f472e811ec5e938240faaeb0e16253af6255fbeaaf367b4cf1074039368b69aad015e7b369a2455848a8344d36cd5fd23d3fb3c0aa36a1c9492566e74a0a3a6b61c049853d0d983b00",
        "serverPublic": "67cd0cfadc66146aed089e581ab4866666923943e3fa1d6f0018067e1fd286df9fa60a7b1bbd0cd7a6bc183303e4fae597c0c7273c178b33b13bf6d2fe6025ed325376540dbb3435b004c9a204993530bc293b9e964e273ddf4ba413dc27da7a010006e45bde18fc91decebe2f252d2b196c5f398c97647f77ce298b72a22a2e4ff13dd59571df29fb4e58cd9676cc32466d0b5d346bbf04133024c81f845d031b41840ac6cb21be98edce76a880f1c5a8b80134e45b1f0738ecabfe6e1cbab36049ad5550cf2325a2ce98558c2d71601b042aa4d1622b4ae918165bbc0807862307c1b5c7de0450cc06edd31b51b804a9243e3173ef75d5307d6d1eb4adf853",
        "sessionKey": "ee231a19b4252228d79019a61883b94d5031f8e11bec4742276b450016a2a9e7",
        "proof": "bef7ae69c1e2207222d32f6ae1d36c6451937cde329a69c3b83af4396ae15471",
        "serverProof": "dfb439f4592d29a75ff021fae68a49d0d6f04d1c09c8c0653e944ca243a69bb4"
    },
    {
        "salt": "d634519731645a63fc3ad6a4cd051267667b91b23e86a1e040e6",
        "username": "BOB",
        "password": "",
        "privateKey": "659410f87ddec877ff80a03eb75945a9105283e83836b3dada2d476c7cfb9e63",
        "verifier": "7320c597a3fbac74b9695f7339baa594314d70d7dd959c7bc5098ea6db4e8440783f5579545ced3d54e6533c7060271142aefd8a920cf05bfc07937f8036647fec0814fb3a356c17ac2e1ba974927188a7be507f6a3be5d105c3788a2dca509a6fd7d36bddf90e1caecd7e311faff3348c3605727a7162447b5ed1d4833341ad78ec6447f688d49c47a68d68eecfbecb4d72c46595dea81b829dbf6903bac18aafed8cf9ab73d1adb254c757db970b7283cc6ff0986c5b1e586e91f1c6a5020bb19375686549a47a4b8e76760692be2c167f938be0f2e4d88ff761ad1f92849b7cf86a181f856b0a6d1b3526ac10aa48103d0135e75f6fe1b04f389e457a4b1e",
        "clientSecret": "2366809e221e9547d29fa8ef51b9c194acc600c6fec0cd3a867852363a5758e0",
        "clientPublic": "7b2597214c42158b1a60fc3d0f5490cfe6c0e1114c6f1d753282c677a80caca53910691c2dbcc63f6848927e01de9bf65cd0226174ed041492a2f65b4e5a3a6de00255ab9c34ffba7151d11c6606b7a769f71f53754bdc2cfc2863c693b62fa43fe1c9cb9eadf6e428df4469be92f7bd2e4f9a75feebc1ed9bc8487c8a8251be423fa7b20f3529f780160e8f7a5630a8d4ea8b75476e996a58fc05396dc15427a576817214932ef98a286e79d893f8be2c68d1599f51403ea1df813d8f007830558af2bc80214e57b164d6882ba812e1d90dce9af229c0f4287106361b56abec6be36e68891333ef48350159607b9038e0e91af30b82d663c84eba1095ac3cd5",
        "serverPublic": "509c4aa9cbd9104b2fd2856d4c552682ff8aa3945fc30d5fcf44170d04add861fdc17286e72cc5c48b92a51ae8d7b26d242b42dbb5c01534016379835373b7c7a3e3494fb2d796724239d0af6e7022df2862bde4f11b1dfb310fc29c270dd73a2f347dceba03ad8ee82781504b97f456f252f3c57b7f13c4459aff93dff52dd4f53291891c1b0d48d391693963556d83ca0f952f428e95e215a3f714bd8b9fd82ba2950256ee12a4de191d7fd942c05b375a23bc0537160237e4495ad4b95f0a0bd8fccc8a605be619a2462725fabfd1c19c230f1ef26f250bc891aa52f02a7d0a0f8ad1ae517231c24bed1b88bb0f6b1a9394ab09b8f94fe586bf5a1e5c668d",
        "sessionKey": "6b33ee6f8044f3a77bdb63dbf1cdb606e1430038fc9ddfc9eb6c6bff2452733d",
        "proof": "65c65401c2f555efd3bcfaecbbe84f7c4114a30d17a34f1f7894d242b515456a",
        "serverProof": "7608a1824152df810f1f8bf1b72777ad9b8c1c69e3a58b7044faba76cfabad3c"
    },
    {
        "salt": "dd63bbdde2a65ec0ebdbe6fc5e35fd604cafa19589ad034270fe5a9f61",
        "username": "alice@x.com",
        "password": "pw",
        "privateKey": "2dae36752654ffb6038f7cd35928161f35fb022b2d345a253148547c7b160d82",
        "verifier": "231ce153e8973885d63e06e4a679a3e64c239135b7a34aa91303a0789dcec9e7417ca1f0497c75a810671d59996a8fa2deb9cda3351e1144f5587df25260074d4df84bb4c4ab771f842c74bc7f7ac39b471c64fb037fe23663499f5e674c4b76b30b4bf25eb1722a6c31a22a9414b96cf95a332d36b1e01500cb3dbd043ba90c34482f0c0fa9fba2907f15a4c43d7312bf3eab4053d4f4d524d06383396226fed85611a11b44a8d054854d4e06f54e851ec9bdbb55ce584bc8fcf52b3741ce673702c4dbc2cc575ab115083a0d28ee20272abd615a03c2cd96349f692d6cbf4089e52da438b71dde77d7d8f64e408b90038e50bd47ad4f05b0a270560ac51ca2",
        "clientSecret": "cf919968ff354db903aa21a7b7b08393fb103ca6ec0389b6c0a724d74007d43f",
        "clientPublic": "1c94409e893e89358c0291cc8e470bc06c22bfaef12ecba2ec572cce687dfb73d433549f175b0268d7d407029d0bc835cabc62f75a843dd029705b09da1e7281cb473ff9be5d735ab536589087f806337cf08773d49ab27770cee9b4942d3d35a1b4d269c087cb045878f448ae6ad2c479dcf6ef09a0f8675dad02c6154ed6b64d7ee0950c98e338d1f7029fa46bc904a54c0ac108c89f5377102091c69fe22252486be655654cdd9a3925b47054437d9933c702155635bd9dde407b786c8597caef494147e81b8ffa4b79d48ea26fd20382927b5ede3a4f905d6b877088435e71f9e6a4e6ac40bff87658cfbd17b11d800f9693c89ca43dcf0b0640225d371e",
        "serverPublic": "87de8f6bfbbc6d621495f6a0a4533a25a3555bedaae074710073a203709ec6dfaf2905cac07d9cad4ad07e873acf32c351fce7fe44be7e517b45ca28df7a1c2ad3f776606b01c6e00f2ae2b712c86f560f3952b2b06268091e5eee16551272309cbbaf65341dcbf1e425f6db11b7d3058861c1957f5cf9ced6b367797a006184c9fdf63fc525ff18f3f786e35533083458d40707579a92ee998e03845a07b94e06a512fc09f88cd251e5d4fd60e521baf937d344b67bd1e8147dd3de5a17a13ddb95cf6c76f094917a9edab40084eb7f6f559c0cd417fdb3a4c08623a291757c948a718465ffc9cd86b972a3cf42ecb517fe58070a3069fa419d3f52c9ddae1c",
        "sessionKey": "d8e9b3fa2ac6162b0d8ca5aff0220778a7f7544dfc858ae3a875a8b09ebf3668",
        "proof": "502695dad374ccab0a0936078a814c1ed412e9926e60a905e5bbf1bcfb507463",
        "serverProof": "48dbe537d6caa4792af864e4219b1de01804caf8b99ce00dfc1dfaa6b0e2c05d"
    },
    {
        "salt": "a3df51e9",
        "username": "",
        "password": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "privateKey": "73021c159e28597b6f4cc7762552e869e3839da531a4f459807b27fb7536b546",
        "verifier": "9b5c5b02916e346925d930f6b188287345877b684e1957beb05498c9c887e259edc2bff78d375b9a4422013c4e8f77badb4d4276cbee22c388aa020e3ece17288ba1659ec52e4d7f98ed87396345b37f2e4f659abf363bcdf4e8eb71fb70ff81e5621c5345667b02923c5df2a6177c44ea0989cbda7dbd04c8671e7d7e2b531c48dd2662c09fe3f682a7118558040ac2471b14dbc7a2759e17ea52401a3bc84350b00a2373c2f9fc6a5e6ea3cb6f3ccec5082e605d9ba56636a8171a60c12fa7da142d2b5c045068e7930b60efefa2ec94d771bb0d78b309fd3fb27a56ce164b20623eeff25041a3ea525e81627f37c714959ec9d059db5d6fe549847586ead1",
        "clientSecret": "18112fba28fd3ae90aebc22ba6a58ec0d88bab9934cb6188fb8e1aac135d04f8",
        "clientPublic": "5f74202c2f3d9509aabdd7f3611a52cabbd3087fc82a9f9f34c72d2a3dd0527e6dae8ff097eca8cebf5413736844134e6194b7767d3be0e00320914fa093e007d3952237e900c1942ae6c798384a4994333417bd5729fa3da8b648b97ddca09b47bca1f1cc97d98c60084416002c0453fbbc46c60174b35ec31728c2218f93a51d89ef8288fe30ae114e7a64c990d801cbc49a75a99b974857b20845cc3434e9cb6ce59b73d78a722bf8ad3f4daae0e94477b68e4f6cec469f64797d0aecf9ffad1a68e92a52bdff5cde3180474b83d894b460a43194199d7708b7fa629e50bf8d9ab7aa02e02e0fd48a76364b89a63777dde6599e63a1fab7267abe9cbda178",
        "serverPublic": "02c04238aa3cb65c5e41122993e81b296cde6286aa66bc4def9dae7cdae72a360fb9aa00b5b1d22788468f22b9651c2a85ee55d0cca1fcf879ec0ddaad7376cf0e76bce42671dd26a4c40a7c9a92b5c285e3fab43c08b12cd614654514e492426c2c3d240143dff1009291fb1bf807adb3bb7e6bdc13b6ef631a3382db0fc76ea08aea746bc837ee45170cb8653a2fdcc78f0c5805fd76917878a2861656232b612e378013ac0c7e367461d09059655b6c21a49299677da1808ef5f49bd48236719b580bf2943a4aa1b37d1f4803b26d9b92a2465e17020020fb7fa4295f3099ccebcdaa004bab2955f74ae6a98701086d86227b0618127f567501bd3142c02a",
        "sessionKey": "156a7ba0743fe475ba262b5ea9cdafb7add0654ab3c3b832f53646dd060673cc",
        "proof": "4e3cdfe3ef68d1b9632fda9566cf7917820acf7572b76602287953bba580d1d9",
        "serverProof": "454fc3f3dae13df7f4f6652f1e10951875f4dfe5df91a8794cdbac9d5d7d6a3f"
    },
    {
        "salt": "6860b189a0ead28131d6bdc9e1ad85aa",
        "username": "x:y:z",
        "password": "a7cd344369b9d314",
        "privateKey": "e9edc770f399d1d5055dd645f76736f8f5f87a96613ed133c566404fcfef6933",
        "verifier": "65bec70608ed474cb446eca9755ed3e4b671c97484861a0463aaee859b834152fd4a34914d4c520f8230cefa08f432664d1a1a12da0fe215cb19192353c1bc926a2c700fd563387b69f668b659d4da660d9e0d223d3461797961459df45f47d79226700c1e92c820f1f3f2ea998c1ae617a9f5bbe815523a86fa5b88208cc2b51b099ec6f91da98aa5da415d715ed956cf0fa576c67940c5b9a4552f47b49f793241dc15c0ef23bea788432a10aa617af91048c1d1985387e87e2816b290cab617ae721fbbc52ac97319372dec10b223a75abc2eb3c654bf5e756bb093742c9434edee22cfa04e6c143211aaf39adb0fbbc3b58fd249f509b1123756eb5baa17",
        "clientSecret": "4b27ac6904b61e1c74b01c832972ba3a6c61d12ce06fe046e7bce8632ab6d745",
        "clientPublic": "674a93e63ed35465a25211fa125efa8cd2727688301e1326474fb1287672aee07941e5186ccf93943d9ec4a67507fc6a0b1f432af5c16e829d60de923b3a791ee5c8e18fe72835d21b712ccd4454c14dd1f949cdd6b032230056da3955b19b27d534db77178705365dab28c7b0576d1a2e4f3be9b854b9da8b1890167068a0eb46d55b0e95bba60fa57ff035f8776fb9b02f6923a76e5321980a8765d0d5c1f51d5702d3883782ee1ae121957c83ab4c4e59199d124357915e36adabed814e651492f3f484eaf826d83dda2822d9c778b74cf9bf59539a54c171385c1dc482307dcf3872967a70a40b6d6bf0aa08c71b39927ee9140044cab671c71e34755baa",
        "serverPublic": "81081ab78ff1602befee2d78ad35869322de97c3737305662b29868e140744436db3a487af979cf9e42843c8e2315d66e0291ffa048214ba5b9b925ac483cde439e02c254f7ba0512d4fcbbb421338cd3b4f67d4f837dbcac889223bdaeab553d45e799375f28a468a8740210be3e15c64f3e5825ffbce3b6d6f1519fe4dcfc07ba7ca2b16dbfdba013b5f6b17008f0d23252a37708478d205c09f8fd1b58e5650283fcc6579af8c485764276dd6b36631aaaf4f3472fe53c7d36ad70eb26d9c955ea6142600346b676151008578c0e30787f6d04b2be1897a76aaa31ad64011d5159db2eb56115956a3cb244a0bfc3896f18f73b60dfe7477f55352175b16ed",
        "sessionKey": "a34a09e2681f8055b7728344d053ff7e51c91af0861915509c0f77a80d115edb",
        "proof": "045c961fe376835d213bbb1a837eb0defffe8af4cc71b4ca4f8d812eaae780bf",
        "serverProof": "a70bb52389a6e87d1ed5d4f91a69280262567deedea99b6d6cea91165b7b6a16"
    },
    {
        "salt": "163bee66195d263c",
        "username": "BOB",
        "password": "",
        "privateKey": "1a9bf485916a27bbcda947251b1e5847ed77355663c1c818f153fe71fbd54c50",
        "verifier": "79856ea43d003bae3e31545ceeed8561360381ead1463f671fd36cacb5e2c09cfe880f025d29bcf7f1f9a4ff5ab98da3b8e04892e45c40ad5ee24b6ad7493f4e4144bf41fd08f5ea8e39943a8120fc768f9b6bfcc4d31f64f559ff62894f4c9053e9e8f31492775e29f100f783ed5abade156f26bba420fd3160a332dd6931e0b69a2acd5d0fd4af23116f5dcf7da4a60edbfd9170b4e360148e12afa83d9e87be004f8a4f64a6dacc15445309ab695cf926f3b0049e9689b18b93b6cfd3a20054600787bd7ff13b7889e001873dde75cfb4816bc38615e6fd18e8c4bfab434358655f65e47e94b4b129b478b08c432e257de2795ade43e1439a509a212c1105",
        "clientSecret": "baa941f53b3368401eb229d3870e304abf522145d24433692626aa8403f56388",
        "clientPublic": "6c9093be83f7d2b72f6b2a7f4ba4e653f62533fd7ddabc15827c1c79fbb91da6dc218b4f25c140edf92e80510d5fb7aa3a78b45523961870f0ac9b9e7646edeb39884b41ddd9b9dc72f048e6cd79ace58eef9d4c7ca5a600d01eb2e5b285114baf64d83c1e94faf645643ad647dc917c0fe730e029209cab08f0acae0d126e4cdaefa1f48c22bd4170275766f206e462ac8bb071d193556122448bf365010632938a0aa2fe87481aec17c0b92ae22d23b1636328d17922711dbfed72da5b689c559d61f732f997e7c42847d79d55dfe751bdddef082b283d609bf16c13e9e72625db3f041e39c3024a5eb4263ae0110d4b5c62fbcc79524a9f502835c0b47fda",
        "serverPublic": "756a1bffb9c5cdbbe759562d5372a9d92073f74b02a229409d91901771cdb7ab34d2963b52997c54f70bd54d874eb89992d55d8078b3d01a328b8260c6e506d703903f44d65b59cd6eea2f1e297660a7e298c6adc657c565ad3dec38db25c67aadc4196e58262e64125c5e7273867405d6c8cebacc408b1c66e0875445d1d21483dbaec8881b97e7b4844c49f807aa6a52e9afada4daf8d34e1bcbf9bce35e7330232bd081f265a987a8d00bb4a3b7c7fc04d237bcd852073338d606e019048601f83bfe8b2e7cb5c73b72a1bd891baef458c7747cd8df5b64dca3622cd3ec52a44acc8c11c73d5cb30a25b56f3add442cbdb7e5ac6d6f69b44cb6f0c93fd949",
        "sessionKey": "9bf3c25a0205e726ed5c3002472a85633c63a661169103a82bcdb30d3fbb58f4",
        "proof": "25031f840bbf2984a130ea88920ea8de45bf852a57f5978e87b3c240fc73bd72",
        "serverProof": "ef12d09d08b92b03d73f76f48dee977fbf7679898a7405368cb21f85c3391c60"
    }
]


@pytest.fixture(params=JS_VECTORS, ids=lambda v: f"salt{len(v['salt'])}-{v['username'] or 'empty'}")
def vector(request):
    return request.param


class TestAgainstJavaScript:
    """Every derivation must match GMGN's bundled JavaScript byte for byte."""

    def test_derive_private_key(self, vector):
        assert (
            srp.derive_private_key(
                vector["salt"], vector["username"], vector["password"]
            )
            == vector["privateKey"]
        )

    def test_derive_verifier(self, vector):
        assert srp.derive_verifier(vector["privateKey"]) == vector["verifier"]

    def test_derive_session_proof(self, vector):
        session = srp.derive_session(
            vector["clientSecret"],
            vector["serverPublic"],
            vector["salt"],
            vector["username"],
            vector["privateKey"],
        )
        assert session.proof == vector["proof"]
        assert session.key == vector["sessionKey"]

    def test_verify_server_proof(self, vector):
        """The server's M2, as computed by the JS server, must verify here."""
        session = srp.Session(key=vector["sessionKey"], proof=vector["proof"])
        srp.verify_session(vector["clientPublic"], session, vector["serverProof"])

    def test_public_ephemeral_matches(self, vector):
        """A = g^a mod N, at the full width of N."""
        secret = srp.SRPInteger.from_hex(vector["clientSecret"])
        assert srp.g.mod_pow(secret, srp.N).to_hex() == vector["clientPublic"]


class TestParameters:
    """The group parameters must be the ones GMGN's client uses."""

    def test_prime_is_rfc5054_2048_bit(self):
        assert srp.N.value.bit_length() == 2048
        assert srp.N.hex_length == 512

    def test_generator_is_two(self):
        assert srp.g.value == 2

    def test_multiplier_is_hash_of_n_and_g(self):
        assert srp.k.to_hex() == srp.H(srp.N, srp.g).to_hex()
        # Value read back from the JavaScript params module.
        assert srp.k.to_hex() == (
            "4cba3fb2923e01fb263ddbbb185a01c131c638f2561942e437727e02ca3c266d"
        )


class TestSRPInteger:
    """Fixed-width hex encoding is what makes the proof reproducible."""

    def test_to_hex_pads_to_declared_width(self):
        assert srp.SRPInteger.from_hex("00ff").to_hex() == "00ff"
        assert srp.SRPInteger.from_hex("ff").to_hex() == "ff"

    def test_mod_pow_adopts_modulus_width(self):
        small = srp.SRPInteger.from_hex("02")
        result = small.mod_pow(srp.SRPInteger.from_hex("03"), srp.N)
        assert len(result.to_hex()) == 512
        assert result.value == 8

    def test_mod_normalises_negative_values(self):
        """jsbn reduces into [0, m); a sign-following remainder breaks the proof."""
        seven = srp.SRPInteger.from_hex("07")
        negative = srp.SRPInteger.from_hex("02").subtract(srp.SRPInteger.from_hex("05"))
        assert negative.value == -3
        assert negative.mod(seven).value == 4

    def test_mod_pow_normalises_negative_base(self):
        """The SRP exchange raises a negative base; the result must stay positive.

        jsbn reduces the base into [0, m) before exponentiating, so (-5)^3 mod 7
        is 1. A sign-following remainder would give -6 here and a proof the
        server rejects.
        """
        seven = srp.SRPInteger.from_hex("07")
        negative = srp.SRPInteger.from_hex("02").subtract(srp.SRPInteger.from_hex("07"))
        assert negative.value == -5
        assert negative.mod_pow(srp.SRPInteger.from_hex("03"), seven).value == 1

    def test_to_hex_without_width_is_an_error(self):
        product = srp.SRPInteger.from_hex("02").multiply(srp.SRPInteger.from_hex("03"))
        with pytest.raises(ValueError, match="no specified length"):
            product.to_hex()

    def test_hash_rejects_other_types(self):
        with pytest.raises(TypeError):
            srp.H(42)


class TestHashing:
    """H() concatenates raw bytes for integers and UTF-8 for strings."""

    def test_string_arguments_are_utf8(self):
        import hashlib

        expected = hashlib.sha256("üñí🔐".encode("utf-8")).hexdigest()
        assert srp.H("üñí🔐").to_hex() == expected

    def test_integer_arguments_use_fixed_width_bytes(self):
        import hashlib

        expected = hashlib.sha256(bytes.fromhex("00ff")).hexdigest()
        assert srp.H(srp.SRPInteger.from_hex("00ff")).to_hex() == expected

    def test_leading_zeros_are_significant(self):
        """"00ff" and "ff" are the same number but hash differently."""
        assert (
            srp.H(srp.SRPInteger.from_hex("00ff")).to_hex()
            != srp.H(srp.SRPInteger.from_hex("ff")).to_hex()
        )


class TestSessionDerivation:
    def test_rejects_server_public_that_is_zero_mod_n(self):
        with pytest.raises(ValueError, match="invalid public ephemeral"):
            srp.derive_session(
                "01", "0" * 512, "beef", "alice", srp.derive_private_key("beef", "alice", "pw")
            )

    def test_wrong_password_produces_a_different_proof(self):
        vector = JS_VECTORS[0]
        wrong_key = srp.derive_private_key(
            vector["salt"], vector["username"], vector["password"] + "typo"
        )
        session = srp.derive_session(
            vector["clientSecret"],
            vector["serverPublic"],
            vector["salt"],
            vector["username"],
            wrong_key,
        )
        assert session.proof != vector["proof"]

    def test_verify_session_rejects_a_bad_server_proof(self):
        vector = JS_VECTORS[0]
        session = srp.Session(key=vector["sessionKey"], proof=vector["proof"])
        with pytest.raises(ValueError, match="session proof is invalid"):
            srp.verify_session(vector["clientPublic"], session, "00" * 32)


class TestGeneration:
    def test_ephemeral_public_is_full_width(self):
        ephemeral = srp.generate_ephemeral()
        assert len(ephemeral.public) == 512
        assert len(ephemeral.secret) == 64
        # A = g^a mod N
        expected = srp.g.mod_pow(srp.SRPInteger.from_hex(ephemeral.secret), srp.N)
        assert ephemeral.public == expected.to_hex()

    def test_ephemerals_are_not_reused(self):
        assert srp.generate_ephemeral().secret != srp.generate_ephemeral().secret

    def test_generate_salt_is_32_bytes(self):
        assert len(srp.generate_salt()) == 64

    def test_full_round_trip_with_a_python_server(self):
        """Play the server side in Python and check both proofs agree."""
        import secrets

        salt = srp.generate_salt()
        username, password = "round@trip.test", "s3cret"
        private_key = srp.derive_private_key(salt, username, password)
        verifier = srp.SRPInteger.from_hex(srp.derive_verifier(private_key))

        client = srp.generate_ephemeral()
        b = srp.SRPInteger.from_hex(secrets.token_bytes(32).hex())
        # B = kv + g^b mod N
        B = srp.k.multiply(verifier).add(srp.g.mod_pow(b, srp.N)).mod(srp.N)

        session = srp.derive_session(
            client.secret, B.to_hex(), salt, username, private_key
        )

        # Server: S = (A * v^u)^b mod N
        A = srp.SRPInteger.from_hex(client.public)
        u = srp.H(A, B)
        S = A.multiply(verifier.mod_pow(u, srp.N)).mod(srp.N).mod_pow(b, srp.N)
        K = srp.H(S)
        M = srp.H(
            srp.H(srp.N).xor(srp.H(srp.g)),
            srp.H(username),
            srp.SRPInteger.from_hex(salt),
            A,
            B,
            K,
        )

        assert session.key == K.to_hex()
        assert session.proof == M.to_hex()

        server_proof = srp.H(A, M, K).to_hex()
        srp.verify_session(client.public, session, server_proof)
