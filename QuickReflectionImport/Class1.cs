
using Microsoft.CodeAnalysis.CSharp;
using System.IO;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using System.Collections;
using static System.Net.Mime.MediaTypeNames;
using Microsoft.CodeAnalysis.Text;
using Microsoft.CodeAnalysis;
using System.Collections.Generic;
using System.Linq;
using System.ComponentModel.Design.Serialization;


namespace ReflectLib
{
    public class ReflectClass
    {
        /*        public string[] GetTypes(string DLLPath)
                {
                    Type[] types = null;
                    try
                    {
                        types = Assembly.LoadFile(DLLPath).GetTypes();
                    }
                    catch (Exception e)
                    {
                        if (e is ReflectionTypeLoadException)
                            types = ((ReflectionTypeLoadException)e).Types;
                    }

                    string[] strings = new string[types.Length];
                    for (int i = 0; i < types.Length; i++)
                    {
                        try {
                            strings[i] = types[i].Namespace + types[i].Name;
                        }
                        finally
                        { }

                    }
                    return strings;*/

        public static string[] GetNamespaceMemberNames(string FilePath)
        {
            SyntaxTree tree;
            using (var stream = File.OpenRead(FilePath))
            {
                var sourceText = SourceText.From(stream);

                // Remove all #ifs
                var lines = sourceText.ToString().Split('\n');
                List<string> goodLines = new List<string>();

                foreach (var l in lines)
                {
                    if (!(l.Contains("#if") || l.Contains("#endif")))
                        goodLines.Add(l);
                }
                var newText = string.Join("\n", goodLines.ToArray());
                sourceText = SourceText.From(newText);


                tree = CSharpSyntaxTree.ParseText(sourceText, path: FilePath);
            }

            var ns = "";
            var cs = "";



            List<string> result = new List<string>();
            CompilationUnitSyntax root = tree.GetCompilationUnitRoot();
            foreach (var m in root.Members)
            {

                if (!(m is NamespaceDeclarationSyntax))
                {
                    cs = GetMemberDeclarationName(m);
                    result.Add(cs);
                    continue;
                }
                




                var Namespace = (NamespaceDeclarationSyntax)m;
                ns = Namespace.Name.ToString();


                if (Namespace.Members.Count == 0)
                    return new string[0];


                if (Namespace.Members[0] is NamespaceDeclarationSyntax)
                {
                    var NewNamespace = (NamespaceDeclarationSyntax)m;
                    ns = Namespace.Name.ToString() + "." + NewNamespace.Name.ToString();
                    Namespace = NewNamespace;

                }

                foreach(var sm in Namespace.Members)
                {
                    cs = GetMemberDeclarationName(sm);
                    result.Add(ns + cs);
                }
                
            }
            return result.ToArray();

        }
        public static string GetMemberDeclarationName(MemberDeclarationSyntax member)
        {
            if (member is ClassDeclarationSyntax)
            {
                var Class = (ClassDeclarationSyntax)member;
                return Class.Identifier.ValueText;
            }
            else if (member is EnumDeclarationSyntax)
            {
                var Enum = (EnumDeclarationSyntax)member;
                return Enum.Identifier.ValueText;
            }
            else if (member is StructDeclarationSyntax)
            {
                var Struct = (StructDeclarationSyntax)member;
                return Struct.Identifier.ValueText;
            }
            else if (member is InterfaceDeclarationSyntax)
            {
                var Interface = (InterfaceDeclarationSyntax)member;
                return Interface.Identifier.ValueText;
            }
            else if (member is DelegateDeclarationSyntax)
            {
                var Delegate = (DelegateDeclarationSyntax)member;
                return Delegate.Identifier.ValueText;
            }
            return "";
        }
    }
}
